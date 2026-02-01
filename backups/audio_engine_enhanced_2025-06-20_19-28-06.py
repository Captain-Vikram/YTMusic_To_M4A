#!/usr/bin/env python3
"""
Enhanced VLC-based Audio Engine for Music Player
High-performance audio playback with smooth operation and better queue handling
"""

import os
import time
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum

try:
    import vlc
except ImportError:
    print("WARNING: python-vlc not installed. Music player functionality will be limited.")
    vlc = None

try:
    import mutagen
    # Prefer named imports when available, but fall back gracefully
    MutagenFile = getattr(mutagen, 'File', None)
    try:
        from mutagen.mp4 import MP4Cover
    except Exception:
        MP4Cover = None
    try:
        from mutagen.flac import Picture
    except Exception:
        Picture = None
    # ID3NoHeaderError may live in id3._util on some versions
    try:
        from mutagen.id3 import ID3NoHeaderError
    except Exception:
        try:
            from mutagen.id3._util import ID3NoHeaderError
        except Exception:
            ID3NoHeaderError = Exception
except ImportError:
    print("WARNING: mutagen not installed. Metadata features will be limited.")
    MutagenFile = None
    MP4Cover = None
    Picture = None
    ID3NoHeaderError = Exception

from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex, QMutexLocker
from PyQt5.QtWidgets import QApplication
from PIL import Image
import io


class PlaybackState(Enum):
    """Enum for playback states"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    LOADING = "loading"
    ERROR = "error"


class RepeatMode(Enum):
    """Enum for repeat modes"""
    NONE = "none"
    SINGLE = "single"
    ALL = "all"


@dataclass
class AudioTrack:
    """Optimized audio track with faster metadata loading"""
    file_path: str
    title: str = ""
    artist: str = ""
    album: str = ""
    genre: str = ""
    year: str = ""
    track_number: int = 0
    duration: float = 0.0
    format: str = ""
    bitrate: int = 0
    sample_rate: int = 0
    channels: int = 0
    file_size: int = 0
    cover_art_path: Optional[str] = None
    rating: int = 0
    play_count: int = 0
    last_played: Optional[float] = None
    position: float = 0.0
    _metadata_loaded: bool = False
    
    def __post_init__(self):
        """Initialize basic info without heavy metadata extraction"""
        if os.path.exists(self.file_path):
            self._load_basic_info()
    
    def _load_basic_info(self):
        """Load basic file info quickly"""
        try:
            file_info = Path(self.file_path)
            self.file_size = file_info.stat().st_size
            self.format = file_info.suffix.lower().replace('.', '').upper()
            
            if not self.title:
                self.title = file_info.stem
                
        except Exception as e:
            print(f"Error loading basic info from {self.file_path}: {e}")
    
    def load_metadata(self):
        """Load full metadata on demand"""
        if self._metadata_loaded or not MutagenFile:
            return
            
        try:
            self._extract_metadata()
            self._metadata_loaded = True
        except Exception as e:
            print(f"Error loading metadata from {self.file_path}: {e}")
    
    def _extract_metadata(self):
        """Extract comprehensive metadata from audio file"""
        try:
            file_info = Path(self.file_path)
            self.file_size = file_info.stat().st_size
            self.format = file_info.suffix.lower().replace('.', '').upper()
            
            if not self.title:
                self.title = file_info.stem
            
            if MutagenFile:
                audio_file = MutagenFile(self.file_path)
                if audio_file:
                    # Extract basic metadata
                    self.title = self._get_tag(audio_file, ['TIT2', 'TITLE', '\xa9nam']) or self.title
                    self.artist = self._get_tag(audio_file, ['TPE1', 'ARTIST', '\xa9ART']) or "Unknown Artist"
                    self.album = self._get_tag(audio_file, ['TALB', 'ALBUM', '\xa9alb']) or "Unknown Album"
                    self.genre = self._get_tag(audio_file, ['TCON', 'GENRE', '\xa9gen']) or ""
                    self.year = self._get_tag(audio_file, ['TDRC', 'DATE', '\xa9day']) or ""
                    
                    # Track number
                    track_num = self._get_tag(audio_file, ['TRCK', 'TRACKNUMBER', 'trkn'])
                    if track_num:
                        try:
                            if '/' in str(track_num):
                                self.track_number = int(str(track_num).split('/')[0])
                            else:
                                self.track_number = int(track_num)
                        except (ValueError, TypeError):
                            pass
                    
                    # Audio properties
                    if hasattr(audio_file, 'info'):
                        info = audio_file.info
                        self.duration = getattr(info, 'length', 0.0)
                        self.bitrate = getattr(info, 'bitrate', 0)
                        self.sample_rate = getattr(info, 'samplerate', 0)
                        self.channels = getattr(info, 'channels', 0)
                    
                    # Extract cover art
                    self._extract_cover_art(audio_file)
        
        except Exception as e:
            print(f"Error extracting metadata from {self.file_path}: {e}")
    
    def _get_tag(self, audio_file, tag_names):
        """Get tag value from multiple possible tag names"""
        for tag_name in tag_names:
            try:
                if tag_name in audio_file:
                    value = audio_file[tag_name]
                    if isinstance(value, list) and value:
                        return str(value[0])
                    return str(value)
            except (KeyError, TypeError):
                continue
        return None
    
    def _extract_cover_art(self, audio_file):
        """Extract cover art and save to cache"""
        try:
            cover_data = None
            
            # MP4/M4A files
            if 'covr' in audio_file:
                cover_data = bytes(audio_file['covr'][0])
            
            # ID3 tags (MP3)
            elif 'APIC:' in audio_file:
                cover_data = audio_file['APIC:'].data
            
            # FLAC
            elif hasattr(audio_file, 'pictures') and audio_file.pictures:
                cover_data = audio_file.pictures[0].data
            
            if cover_data:
                # Create cover art cache directory
                cache_dir = Path(os.path.dirname(self.file_path)) / ".music_cache"
                cache_dir.mkdir(exist_ok=True)
                
                cover_filename = f"{Path(self.file_path).stem}_cover.jpg"
                cover_path = cache_dir / cover_filename
                
                # Save cover art
                with open(cover_path, 'wb') as f:
                    f.write(cover_data)
                
                self.cover_art_path = str(cover_path)
        
        except Exception as e:
            print(f"Error extracting cover art: {e}")
    
    def get_display_title(self) -> str:
        """Get formatted display title"""
        if not self._metadata_loaded:
            self.load_metadata()
            
        if self.artist and self.title:
            return f"{self.artist} - {self.title}"
        return self.title or os.path.basename(self.file_path)
    
    def get_duration_str(self) -> str:
        """Get formatted duration string"""
        if self.duration <= 0:
            return "0:00"
        
        minutes = int(self.duration // 60)
        seconds = int(self.duration % 60)
        
        if minutes >= 60:
            hours = minutes // 60
            minutes = minutes % 60
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        
        return f"{minutes}:{seconds:02d}"
    
    def get_file_size_str(self) -> str:
        """Get formatted file size string"""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"


class VLCPlayer(QObject):
    """Enhanced VLC audio player with better performance and smoother operation"""
    
    # Signals for state changes
    state_changed = pyqtSignal(PlaybackState)
    position_changed = pyqtSignal(float)
    duration_changed = pyqtSignal(float)
    volume_changed = pyqtSignal(int)
    track_changed = pyqtSignal(AudioTrack)
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        self.instance = None
        self.player = None
        self.current_track: Optional[AudioTrack] = None
        self.state = PlaybackState.STOPPED
        self.volume = 70
        self.position = 0.0
        self.duration = 0.0
        self._is_seeking = False
        self._next_track_queued = None
        
        # Thread safety
        self._mutex = QMutex()
        
        # Optimized position tracking
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self._update_position)
        self.position_timer.setInterval(50)  # 50ms for smoother updates
        
        # Preloading timer
        self.preload_timer = QTimer()
        self.preload_timer.timeout.connect(self._check_preload)
        self.preload_timer.setInterval(1000)  # Check every second
        
        self._initialize_vlc()
    
    def _initialize_vlc(self):
        """Initialize VLC with optimized settings for smooth playback"""
        if not vlc:
            self.error_occurred.emit("VLC not available. Please install python-vlc and VLC media player.")
            return
        
        try:
            # Optimized VLC arguments for smooth audio playback
            vlc_args = [
                '--intf=dummy',  # No interface
                '--no-video',  # Audio only
                '--audio-resampler=soxr',  # High quality audio resampling
                '--network-caching=1000',  # Network caching
                '--file-caching=300',  # File caching
                '--audio-desync=0',  # No audio desync
                '--gain=1.0',  # Audio gain
                '--volume=100',  # Max volume (we control via software)
                '--no-stats',  # No statistics
                '--no-osd',  # No on-screen display
                '--quiet',  # Quiet mode
                '--no-lua',  # Disable lua scripting
                '--aout=directsound' if os.name == 'nt' else '--aout=pulse',  # Platform-specific audio output
            ]
            
            self.instance = vlc.Instance(vlc_args)
            if not self.instance:
                raise Exception("Failed to create VLC instance")
                
            self.player = self.instance.media_player_new()
            if not self.player:
                raise Exception("Failed to create VLC player")
            
            # Set initial volume
            self.player.audio_set_volume(self.volume)
            
            # Setup event handlers
            self._setup_event_handlers()
            
            print("VLC player initialized successfully")
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to initialize VLC: {e}")
            print(f"VLC initialization error: {e}")
    
    def _setup_event_handlers(self):
        """Setup VLC event handlers"""
        if not self.player:
            return
            
        try:
            event_manager = self.player.event_manager()

            # Attach events safely. Some python-vlc wrappers differ across platforms
            EventType = getattr(vlc, 'EventType', None)
            if EventType is not None:
                pairs = [
                    ('MediaPlayerPlaying', self._on_playing),
                    ('MediaPlayerPaused', self._on_paused),
                    ('MediaPlayerStopped', self._on_stopped),
                    ('MediaPlayerEndReached', self._on_end_reached),
                    ('MediaPlayerEncounteredError', self._on_error),
                ]
                for name, handler in pairs:
                    ev = getattr(EventType, name, None)
                    if ev is not None:
                        try:
                            event_manager.event_attach(ev, handler)
                        except Exception:
                            # Non-fatal: continue if attach fails
                            pass
            
        except Exception as e:
            print(f"Error setting up VLC event handlers: {e}")
    
    def load_track(self, track: AudioTrack) -> bool:
        """Load track with optimized preparation"""
        if not self.player or not os.path.exists(track.file_path):
            return False
        
        with QMutexLocker(self._mutex):
            try:
                self.current_track = track
                self._set_state(PlaybackState.LOADING)
                
                # Load metadata if not already loaded
                if not track._metadata_loaded:
                    track.load_metadata()
                
                # Create media safely (wrappers expose methods differently)
                media = None
                media_new = getattr(self.instance, 'media_new', None)
                if callable(media_new):
                    try:
                        media = media_new(track.file_path)
                    except Exception:
                        media = None
                if not media:
                    raise Exception("Failed to create VLC media")

                # Parse media to get duration, prefer parse_with_options if available
                MediaParseFlag = getattr(vlc, 'MediaParseFlag', None)
                local_flag = getattr(MediaParseFlag, 'local', None) if MediaParseFlag is not None else None
                if hasattr(media, 'parse_with_options') and local_flag is not None:
                    try:
                        media.parse_with_options(local_flag, 500)
                    except Exception:
                        try:
                            media.parse()
                        except Exception:
                            pass
                else:
                    try:
                        media.parse()
                    except Exception:
                        pass
                
                # Set media to player
                self.player.set_media(media)
                
                # Get duration
                duration = media.get_duration()
                if duration > 0:
                    self.duration = duration / 1000.0  # Convert to seconds
                    track.duration = self.duration
                else:
                    self.duration = track.duration
                
                self.duration_changed.emit(self.duration)
                
                # Reset position
                self.position = track.position
                self.position_changed.emit(self.position)
                
                self.track_changed.emit(track)
                
                print(f"Loaded track: {track.get_display_title()}")
                return True
                
            except Exception as e:
                self.error_occurred.emit(f"Failed to load track: {e}")
                print(f"Track loading error: {e}")
                self._set_state(PlaybackState.ERROR)
                return False
    
    def play(self) -> bool:
        """Start or resume playback with smooth transition"""
        if not self.player:
            return False
        
        try:
            result = self.player.play()
            
            if result == 0:  # Success
                # Restore position if needed
                if self.position > 0 and self.duration > 0:
                    QTimer.singleShot(200, lambda: self._restore_position())
                
                return True
            else:
                self.error_occurred.emit("Failed to start playback")
                return False
                
        except Exception as e:
            self.error_occurred.emit(f"Playback error: {e}")
            return False
    
    def _restore_position(self):
        """Restore playback position smoothly"""
        if self.position > 0 and self.duration > 0:
            percentage = min(max(self.position / self.duration, 0.0), 0.99)
            if hasattr(self.player, 'set_position'):
                try:
                    self.player.set_position(percentage)
                except Exception:
                    pass
    
    def pause(self) -> bool:
        """Pause playback"""
        if not self.player:
            return False
        
        try:
            self.player.pause()
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to pause: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop playback"""
        if not self.player:
            return False
        
        try:
            self.player.stop()
            self.position = 0.0
            self.position_changed.emit(0.0)
            
            # Save position to track
            if self.current_track:
                self.current_track.position = 0.0
            
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to stop: {e}")
            return False
    
    def seek(self, position: float) -> bool:
        """Seek to position with smooth operation"""
        if not self.player or self.duration <= 0:
            return False
        
        try:
            with QMutexLocker(self._mutex):
                self._is_seeking = True
                
                # Calculate percentage
                percentage = min(max(position / self.duration, 0.0), 0.99)
                
                # Set position
                if hasattr(self.player, 'set_position'):
                    try:
                        self.player.set_position(percentage)
                    except Exception:
                        pass
                
                # Update internal position
                self.position = position
                
                # Save to track
                if self.current_track:
                    self.current_track.position = position
                
                self.position_changed.emit(position)
                
                # Reset seeking flag after a delay
                QTimer.singleShot(100, lambda: setattr(self, '_is_seeking', False))
                
                return True
                
        except Exception as e:
            self.error_occurred.emit(f"Failed to seek: {e}")
            self._is_seeking = False
            return False
    
    def set_volume(self, volume: int) -> bool:
        """Set volume with smooth adjustment"""
        if not self.player:
            return False
        
        try:
            volume = max(0, min(100, volume))
            self.player.audio_set_volume(volume)
            self.volume = volume
            self.volume_changed.emit(volume)
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to set volume: {e}")
            return False
    
    def preload_next_track(self, track: AudioTrack):
        """Preload next track for gapless playback"""
        self._next_track_queued = track
    
    def get_position(self) -> float:
        return self.position
    
    def get_duration(self) -> float:
        return self.duration
    
    def get_state(self) -> PlaybackState:
        return self.state
    
    def get_volume(self) -> int:
        return self.volume
    
    def is_playing(self) -> bool:
        return self.state == PlaybackState.PLAYING
    
    def is_paused(self) -> bool:
        return self.state == PlaybackState.PAUSED
    
    def _set_state(self, new_state: PlaybackState):
        """Set state and manage timers"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            
            # Manage position timer
            if new_state == PlaybackState.PLAYING:
                self.position_timer.start()
                self.preload_timer.start()
            elif new_state in [PlaybackState.STOPPED, PlaybackState.PAUSED, PlaybackState.ERROR]:
                self.position_timer.stop()
                if new_state == PlaybackState.STOPPED:
                    self.preload_timer.stop()
            
            self.state_changed.emit(new_state)
            print(f"State changed: {old_state.value} -> {new_state.value}")
    
    def _update_position(self):
        """Update position with smooth tracking"""
        if not self.player or self._is_seeking:
            return
        
        try:
            if self.state == PlaybackState.PLAYING:
                # Get position from VLC
                vlc_position = self.player.get_position()
                
                if vlc_position >= 0 and self.duration > 0:
                    new_position = vlc_position * self.duration
                    
                    # Only emit if position changed significantly
                    if abs(new_position - self.position) > 0.1:
                        self.position = new_position
                        self.position_changed.emit(self.position)
                        
                        # Save to track
                        if self.current_track:
                            self.current_track.position = self.position
                            
        except Exception as e:
            pass  # Ignore position update errors
    
    def _check_preload(self):
        """Check if we should preload next track"""
        if (self.state == PlaybackState.PLAYING and 
            self.duration > 0 and 
            self.position > 0 and
            (self.duration - self.position) < 10):  # 10 seconds before end
            
            if self._next_track_queued:
                print("Preloading next track for gapless playback")
    
    # VLC Event Handlers
    def _on_playing(self, event):
        self._set_state(PlaybackState.PLAYING)
    
    def _on_paused(self, event):
        self._set_state(PlaybackState.PAUSED)
    
    def _on_stopped(self, event):
        self._set_state(PlaybackState.STOPPED)
    
    def _on_end_reached(self, event):
        self._set_state(PlaybackState.STOPPED)
        if self.current_track:
            self.current_track.position = 0.0
            self.current_track.play_count += 1
            self.current_track.last_played = time.time()
    
    def _on_error(self, event):
        self._set_state(PlaybackState.ERROR)
        self.error_occurred.emit("VLC playback error")
    
    def cleanup(self):
        """Clean up resources"""
        print("Cleaning up VLC player...")
        
        if self.position_timer:
            self.position_timer.stop()
        
        if self.preload_timer:
            self.preload_timer.stop()
        
        if self.player:
            try:
                self.player.stop()
                self.player.release()
            except:
                pass
        
        if self.instance:
            try:
                self.instance.release()
            except:
                pass
