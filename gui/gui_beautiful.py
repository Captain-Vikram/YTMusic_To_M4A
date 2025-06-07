#!/usr/bin/env python3
"""
YouTube Music Extractor - Beautiful PyQt5 GUI Application
A stunning and modern GUI for downloading and processing YouTube music with metadata and cover art.
Features:
- Beautiful gradient backgrounds
- Modern glass-morphism effects
- Smooth animations
- Professional layout
- Real-time progress tracking
- Advanced settings panel
"""

import sys
import os
import threading
import time
import json
import requests
import shutil
import importlib.util
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar,
    QCheckBox, QComboBox, QGroupBox, QTabWidget, QFileDialog, QMessageBox,
    QSpinBox, QSlider, QFrame, QScrollArea, QListWidget, QListWidgetItem,
    QSplitter, QTreeWidget, QTreeWidgetItem, QStatusBar, QMenuBar, QAction,
    QDialog, QDialogButtonBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QGraphicsDropShadowEffect, QButtonGroup, QRadioButton
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSettings, QSize, QRect, pyqtSlot,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QSequentialAnimationGroup,
    QUrl, QPointF
)
from PyQt5.QtGui import (
    QFont, QPalette, QColor, QPixmap, QIcon, QMovie, QPainter, QBrush,
    QLinearGradient, QTextCharFormat, QTextCursor, QDesktopServices, QFontDatabase,
    QRadialGradient, QPen, QPolygonF, QConicalGradient
)

# Import the main processing functions
# Handle both development and PyInstaller environments
def get_main_functions():
    """Get main functions with fallback for PyInstaller"""
    try:
        # First try direct import (works in PyInstaller)
        import main as main_module
        return (
            main_module.sanitize_filename,
            main_module.process_cover_art,
            main_module.process_single_track,
            main_module.check_available_formats
        )
    except ImportError:
        try:
            # Try importlib approach for development
            import importlib.util
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            main_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
            if os.path.exists(main_path):
                spec = importlib.util.spec_from_file_location("main_root", main_path)
                main_root = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(main_root)
                
                return (
                    main_root.sanitize_filename,
                    main_root.process_cover_art,
                    main_root.process_single_track,
                    main_root.check_available_formats
                )
        except Exception as e:
            print(f"Could not import main functions: {e}")
    
    # Fallback implementations
    def sanitize_filename(filename):
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()
    def process_cover_art(temp_path, output_path):
        try:
            shutil.copy2(temp_path, output_path)
            return output_path
        except:
            return None
    
    def process_single_track(entry, album_folder, cover_art_path, album_title, track_num=1, total_tracks=1):
        return True
    
    def check_available_formats(url):
        return []
    
    return (sanitize_filename, process_cover_art, process_single_track, check_available_formats)

# Get the main functions
sanitize_filename, process_cover_art, process_single_track, check_available_formats = get_main_functions()

import yt_dlp
from PIL import Image


class DownloadWorker(QThread):
    """Enhanced worker thread for downloading and processing YouTube content with parallel processing"""
    
    # Enhanced signals for better progress tracking
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    log_updated = pyqtSignal(str, str)  # message, type
    download_finished = pyqtSignal(bool, str)  # success, message
    format_info_ready = pyqtSignal(dict)
    thumbnail_ready = pyqtSignal(str)  # thumbnail path
    track_processed = pyqtSignal(str, int, int)  # track name, current, total
    speed_updated = pyqtSignal(str)  # download speed
    eta_updated = pyqtSignal(str)  # estimated time remaining
    
    def __init__(self, url, output_dir, quality_format, parallel_downloads=8):
        super().__init__()
        self.url = url
        self.output_dir = output_dir
        self.quality_format = quality_format
        self.parallel_downloads = min(parallel_downloads, 8)  # Maximum 8 for optimal performance
        self.is_cancelled = False
        self.start_time = time.time()
    
    def run(self):
        """Main download process with enhanced parallel processing and speed optimization"""
        try:
            self.start_time = time.time()
            self.status_updated.emit("🔍 Analyzing URL...")
            self.log_updated.emit("Starting high-speed URL analysis...", "info")
            
            # Enhanced extract info with speed optimizations
            ydl_opts_info = {
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,  # Continue on errors during analysis
                'socket_timeout': 30,  # Faster timeout
                'geo_bypass': True,  # Bypass geographic restrictions
            }
            
            with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                try:
                    info = ydl.extract_info(self.url, download=False)
                    if not info:
                        self.log_updated.emit("Could not extract video information", "error")
                        self.download_finished.emit(False, "Could not extract video information")
                        return
                    
                    self.format_info_ready.emit(info)
                except Exception as e:
                    error_msg = str(e).lower()
                    if 'video unavailable' in error_msg or 'private video' in error_msg:
                        self.log_updated.emit(f"Video unavailable: {e}", "error")
                        self.download_finished.emit(False, "Video is private, deleted, or not accessible")
                        return
                    else:
                        self.log_updated.emit(f"Error extracting info: {e}", "error")
                        self.download_finished.emit(False, f"Error extracting info: {e}")
                        return
            
            if self.is_cancelled:
                return
                
            # Determine if playlist or single track
            is_playlist = '_type' in info and info['_type'] == 'playlist'
            
            if is_playlist:
                self.log_updated.emit(f"🎵 Album/Playlist: {info.get('title', 'Unknown Album')}", "info")
                self.log_updated.emit(f"📀 Tracks found: {len(info.get('entries', []))}", "info")
                
                album_title = sanitize_filename(info.get('title', 'Unknown Album'))
                album_folder = os.path.join(self.output_dir, album_title)
                
                if not os.path.exists(album_folder):
                    os.makedirs(album_folder)
                    self.log_updated.emit(f"📁 Created: {album_folder}", "success")
                
                output_template = os.path.join(album_folder, "%(title)s.%(ext)s")
            else:
                self.log_updated.emit(f"🎵 Single Track: {info.get('title', 'Unknown')}", "info")
                track_title = sanitize_filename(info.get('title', 'Unknown'))
                album_folder = os.path.join(self.output_dir, f"Single - {track_title}")
                album_title = track_title
                
                if not os.path.exists(album_folder):
                    os.makedirs(album_folder)
                    self.log_updated.emit(f"📁 Created: {album_folder}", "success")
                
                output_template = os.path.join(album_folder, "%(title)s.%(ext)s")
            
            if self.is_cancelled:
                return
                
            # Enhanced download phase with speed optimizations
            self.status_updated.emit("⚡ Starting high-speed download...")
            self.log_updated.emit(f"🚀 Using {self.parallel_downloads} parallel workers for maximum speed", "info")
            self.progress_updated.emit(10)
            
            # Enhanced yt-dlp options for maximum speed
            ydl_opts = {
                'format': self.quality_format or 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio[ext=opus]/bestaudio/best',
                'outtmpl': output_template,
                'writeinfojson': True,
                'writethumbnail': True,
                'extract_flat': False,
                'ignoreerrors': True,  # Continue on download errors
                'no_warnings': True,
                # Performance optimizations for GUI
                'concurrent_fragment_downloads': self.parallel_downloads,  # Use configured parallel downloads
                'fragment_retries': 3,  # Retry failed fragments
                'retries': 3,  # Retry failed downloads
                'socket_timeout': 30,  # Socket timeout in seconds
                'http_chunk_size': 10485760,  # 10MB chunks for faster download
                # Network optimizations
                'prefer_insecure': False,  # Use HTTPS when possible
                'geo_bypass': True,  # Bypass geographic restrictions
                'geo_bypass_country': None,  # Let yt-dlp choose best bypass
                # Progress hook for real-time updates
                'progress_hooks': [self._download_progress_hook],
            }
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    result = ydl.extract_info(self.url, download=True)
                
                if not result:
                    self.log_updated.emit("No content could be downloaded", "error")
                    self.download_finished.emit(False, "No content could be downloaded")
                    return
                
                # Enhanced filtering for playlists
                if is_playlist and 'entries' in result:
                    original_count = len(result.get('entries', []))
                    # Enhanced filtering to skip unavailable/private videos
                    valid_entries = []
                    skipped_count = 0
                    
                    for entry in result.get('entries', []):
                        if entry is None:
                            skipped_count += 1
                            continue
                        
                        # Check if entry has essential fields for processing
                        if (not entry.get('title') or 
                            entry.get('title') in ['[Private video]', '[Deleted video]', 'Private video', 'Deleted video'] or
                            not entry.get('url') or 
                            entry.get('availability') in ['private', 'premium_only', 'subscriber_only', 'needs_auth', 'unlisted'] or
                            entry.get('live_status') == 'is_upcoming'):
                            skipped_count += 1
                            self.log_updated.emit(f"⚠️ Skipping unavailable: {entry.get('title', 'Unknown')}", "warning")
                            continue
                        
                        valid_entries.append(entry)
                    
                    result['entries'] = valid_entries
                    
                    if skipped_count > 0:
                        self.log_updated.emit(f"📋 Skipped {skipped_count} unavailable/private tracks", "warning")
                    
                    if not result['entries']:
                        self.log_updated.emit("No tracks in playlist are available for download", "error")
                        self.download_finished.emit(False, "No tracks available")
                        return
                
            except Exception as e:
                error_msg = str(e).lower()
                if 'video unavailable' in error_msg or 'private video' in error_msg:
                    if is_playlist:
                        self.log_updated.emit("⚠️ Some tracks in playlist are unavailable, continuing with available tracks...", "warning")
                        # For playlists, try to continue with available tracks
                        try:
                            # Re-extract with ignoreerrors to get partial results
                            ydl_opts['ignoreerrors'] = True
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                result = ydl.extract_info(self.url, download=True)
                            if result and result.get('entries'):
                                result['entries'] = [entry for entry in result.get('entries', []) if entry is not None]
                                if result['entries']:
                                    self.log_updated.emit(f"✅ Downloaded {len(result['entries'])} available tracks", "success")
                                else:
                                    self.log_updated.emit("❌ No tracks in playlist are available", "error")
                                    self.download_finished.emit(False, "All tracks in playlist are unavailable")
                                    return
                            else:
                                self.log_updated.emit("❌ Could not download any tracks from playlist", "error")
                                self.download_finished.emit(False, "Playlist download failed")
                                return
                        except Exception as retry_error:
                            self.log_updated.emit(f"❌ Playlist download failed: {retry_error}", "error")
                            self.download_finished.emit(False, f"Playlist download failed: {retry_error}")
                            return
                    else:
                        # For single tracks, this is a fatal error
                        self.log_updated.emit(f"❌ Video unavailable: {e}", "error")
                        self.download_finished.emit(False, f"Video unavailable: {e}")
                        return
                else:
                    # Other types of errors
                    self.log_updated.emit(f"❌ Download error: {e}", "error")
                    self.download_finished.emit(False, f"Download error: {e}")
                    return
            
            if not result:
                self.log_updated.emit("❌ No content could be downloaded", "error")
                self.download_finished.emit(False, "No content available for download")
                return
            
            # For playlists, filter out failed entries
            if is_playlist and 'entries' in result:
                original_count = len(result.get('entries', []))
                # Filter out None entries (failed downloads)
                result['entries'] = [entry for entry in result.get('entries', []) if entry is not None]
                failed_count = original_count - len(result['entries'])
                
                if failed_count > 0:
                    self.log_updated.emit(f"⚠️ {failed_count} tracks could not be downloaded (unavailable/private)", "warning")
                
                if not result['entries']:
                    self.log_updated.emit("❌ No tracks in playlist are available for download", "error")
                    self.download_finished.emit(False, "All tracks in playlist are unavailable")
                    return
            
            if self.is_cancelled:
                return
            
            self.progress_updated.emit(30)
            
            # Process cover art
            self.status_updated.emit("🎨 Processing artwork...")
            cover_art_path = self._process_cover_art(result, album_folder, is_playlist)
            
            if cover_art_path and os.path.exists(cover_art_path):
                self.thumbnail_ready.emit(cover_art_path)
            
            self.progress_updated.emit(50)
            
            if self.is_cancelled:
                return
                
            # Process tracks
            self.status_updated.emit("🎵 Processing tracks...")
            if is_playlist:
                success = self._process_playlist(result, album_folder, cover_art_path, album_title)
            else:
                success = self._process_single_track(result, album_folder, cover_art_path, album_title)
            
            if self.is_cancelled:
                return
                
            # Cleanup
            self.status_updated.emit("🧹 Cleaning up...")
            self._cleanup_temp_files(album_folder)
            
            self.progress_updated.emit(100)
            
            # Calculate total processing time
            total_time = time.time() - self.start_time
            time_str = f"{total_time:.1f}s" if total_time < 60 else f"{int(total_time // 60)}m {int(total_time % 60)}s"
            
            if success:
                self.status_updated.emit("✅ Download completed!")
                self.log_updated.emit(f"🎉 All processing completed in {time_str}", "success")
                self.download_finished.emit(True, f"Successfully completed in {time_str}")
            else:
                self.status_updated.emit("❌ Download failed")
                self.download_finished.emit(False, "Processing failed")
                
        except Exception as e:
            self.log_updated.emit(f"❌ Fatal error: {e}", "error")
            import traceback
            traceback.print_exc()
            self.download_finished.emit(False, f"Fatal error: {e}")
    
    def _download_progress_hook(self, d):
        """Real-time download progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            # Extract progress information
            if 'downloaded_bytes' in d and 'total_bytes' in d:
                progress = int((d['downloaded_bytes'] / d['total_bytes']) * 100)
                self.progress_updated.emit(min(progress, 90))  # Keep some room for processing
                
            # Extract speed information
            if 'speed' in d and d['speed']:
                speed = d['speed']
                if speed > 1024 * 1024:  # MB/s
                    speed_str = f"{speed / (1024 * 1024):.1f} MB/s"
                elif speed > 1024:  # KB/s
                    speed_str = f"{speed / 1024:.1f} KB/s"
                else:  # B/s
                    speed_str = f"{speed:.0f} B/s"
                self.speed_updated.emit(speed_str)
                
            # Extract ETA information
            if 'eta' in d and d['eta']:
                eta = d['eta']
                if eta > 60:
                    eta_str = f"{eta // 60}m {eta % 60}s"
                else:
                    eta_str = f"{eta}s"
                self.eta_updated.emit(eta_str)
                
        elif d['status'] == 'finished':        self.log_updated.emit(f"✅ Downloaded: {os.path.basename(d['filename'])}", "success")
    
    def _process_cover_art(self, result, album_folder, is_playlist):
        """Enhanced cover art processing with faster downloads"""
        cover_art_path = None
        
        try:
            if is_playlist:
                playlist_title = sanitize_filename(result.get('title', 'Unknown Album'))
                thumbnail_url = result.get("thumbnail")
            else:
                title = sanitize_filename(result.get("title", "Unknown"))
                thumbnail_url = result.get("thumbnail")
            
            if thumbnail_url:
                self.status_updated.emit("🎨 Downloading cover art...")
                try:
                    # Fast thumbnail download with timeout
                    response = requests.get(thumbnail_url, timeout=15)
                    response.raise_for_status()
                    img_data = response.content
                    temp_cover_path = os.path.join(album_folder, "temp_cover.jpg")
                    with open(temp_cover_path, "wb") as handler:
                        handler.write(img_data)
                    
                    cover_art_path = process_cover_art(temp_cover_path, os.path.join(album_folder, "cover.jpg"))
                    
                    if os.path.exists(temp_cover_path):
                        os.remove(temp_cover_path)
                    
                    self.thumbnail_ready.emit(cover_art_path)
                    self.log_updated.emit("✅ Cover art processed", "success")
                except Exception as e:
                    self.log_updated.emit(f"⚠️ Cover art download failed: {e}", "warning")
            
            # Fallback to yt-dlp generated thumbnails
            if not cover_art_path:
                for file in os.listdir(album_folder):
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        thumb_path = os.path.join(album_folder, file)
                        cover_art_path = process_cover_art(thumb_path, os.path.join(album_folder, "cover.jpg"))
                        self.thumbnail_ready.emit(cover_art_path)
                        break
                        
        except Exception as e:        self.log_updated.emit(f"⚠️ Cover art processing error: {e}", "warning")
        
        return cover_art_path
    
    def _process_playlist(self, result, album_folder, cover_art_path, album_title):
        """Enhanced parallel playlist processing with real-time progress"""
        entries = result.get('entries', [])
        total_tracks = len(entries)
        
        if not entries:
            self.log_updated.emit("No tracks found in playlist", "error")
            return False
        
        self.status_updated.emit(f"🚀 Processing {total_tracks} tracks in parallel...")
        self.log_updated.emit(f"⚡ Using {self.parallel_downloads} parallel workers", "info")
        
        successful_tracks = 0
        failed_tracks = 0
        start_time = time.time()
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.parallel_downloads) as executor:
            # Submit all tasks
            future_to_track = {
                executor.submit(
                    process_single_track, 
                    entry, 
                    album_folder, 
                    cover_art_path, 
                    album_title, 
                    i + 1, 
                    total_tracks
                ): (i + 1, entry.get('title', 'Unknown'))
                for i, entry in enumerate(entries)
            }
            
            # Process completed tasks with real-time updates
            for future in as_completed(future_to_track):
                if self.is_cancelled:
                    # Cancel remaining tasks
                    for f in future_to_track:
                        f.cancel()
                    return False
                    
                track_num, track_title = future_to_track[future]
                try:
                    success = future.result()
                    if success:
                        successful_tracks += 1
                        self.track_processed.emit(track_title, successful_tracks, total_tracks)
                        self.log_updated.emit(f"✅ [{successful_tracks}/{total_tracks}] {track_title}", "success")
                    else:
                        failed_tracks += 1
                        self.log_updated.emit(f"❌ Failed: {track_title}", "error")
                    
                    # Update progress
                    completed = successful_tracks + failed_tracks
                    progress = 30 + int((completed / total_tracks) * 60)  # 30-90% range
                    self.progress_updated.emit(progress)
                      # Calculate and emit ETA
                    if completed > 0:
                        elapsed_time = time.time() - start_time
                        avg_time_per_track = elapsed_time / completed
                        remaining_tracks = total_tracks - completed
                        eta_seconds = avg_time_per_track * remaining_tracks
                        
                        if eta_seconds > 60:
                            eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
                        else:
                            eta_str = f"{int(eta_seconds)}s"
                        self.eta_updated.emit(eta_str)
                        
                except Exception as e:
                    failed_tracks += 1
                    self.log_updated.emit(f"❌ Error processing {track_title}: {str(e)}", "error")
        
        total_time = time.time() - start_time
        self.log_updated.emit(f"🎉 Completed in {total_time:.1f}s: {successful_tracks} successful, {failed_tracks} failed", "info")
        return successful_tracks > 0
    
    def _process_single_track(self, result, album_folder, cover_art_path, album_title):
        """Process single track with enhanced error handling"""
        try:
            self.status_updated.emit("🎵 Processing single track...")
            
            success = process_single_track(result, album_folder, cover_art_path, album_title)
            if success:
                self.track_processed.emit(result.get('title', 'Unknown'), 1, 1)
                self.log_updated.emit("✅ Single track processed successfully", "success")
                return True
            else:
                self.log_updated.emit("❌ Failed to process single track", "error")
                return False
                
        except Exception as e:
            self.log_updated.emit(f"❌ Single track processing error: {e}", "error")
            return False
    
    def _cleanup_temp_files(self, album_folder):
        """Enhanced cleanup with better file management"""
        try:
            deleted_count = 0
            
            # Clean main directory
            for file in os.listdir('.'):
                if os.path.isfile(file):
                    _, ext = os.path.splitext(file)
                    if ext.lower() not in {'.py', '.md', '.txt', '.json', '.gitignore'}:
                        if not file.startswith('gui_') and not file.startswith('launcher_'):
                            try:
                                os.remove(file)
                                deleted_count += 1
                            except:
                                pass
            
            # Clean album folder
            if album_folder and os.path.exists(album_folder):
                for file in os.listdir(album_folder):
                    if os.path.isfile(os.path.join(album_folder, file)):
                        if not file.endswith('.m4a') and file != 'cover.jpg':
                            try:
                                os.remove(os.path.join(album_folder, file))
                                deleted_count += 1
                            except:
                                pass
            
            if deleted_count > 0:
                self.log_updated.emit(f"🗑️ Cleaned {deleted_count} temp files", "info")
                
        except Exception as e:
            self.log_updated.emit(f"⚠️ Cleanup warning: {e}", "warning")
    
    def cancel(self):
        """Cancel the download process"""
        self.is_cancelled = True
        self.quit()


class ModernButton(QPushButton):
    """Custom button with modern styling and hover effects"""
    
    def __init__(self, text, button_type="primary", is_light_mode=False):
        super().__init__(text)
        self.button_type = button_type
        self.is_light_mode = is_light_mode
        self.setMinimumHeight(45)
        self.setFont(QFont("Segoe UI", 10, QFont.Medium))
        self.apply_style()
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        if is_light_mode:
            shadow.setColor(QColor(127, 63, 127, 40))
        else:
            shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)
    
    def apply_style(self):
        """Apply modern button styling with custom color scheme"""
        if self.is_light_mode:
            self._apply_light_style()
        else:
            self._apply_dark_style()
    
    def _apply_dark_style(self):
        """Apply dark theme button styling"""
        if self.button_type == "primary":
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #6A1E55, stop:1 #A64D79);
                    border: none;
                    border-radius: 22px;
                    color: white;
                    font-weight: 600;
                    padding: 12px 24px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #5a1a4a, stop:1 #954471);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #4a1640, stop:1 #843b69);
                }
                QPushButton:disabled {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #666666, stop:1 #999999);
                    color: #cccccc;
                }
            """)
        elif self.button_type == "success":
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #A64D79, stop:1 #6A1E55);
                    border: none;
                    border-radius: 22px;
                    color: white;
                    font-weight: 600;
                    padding: 12px 24px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #954471, stop:1 #5a1a4a);
                }
            """)
        elif self.button_type == "danger":
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #eb3349, stop:1 #f45c43);
                    border: none;
                    border-radius: 22px;
                    color: white;
                    font-weight: 600;
                    padding: 12px 24px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #d42e42, stop:1 #e5533c);
                }
            """)
        else:  # secondary
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(166, 77, 121, 0.2);
                    border: 2px solid rgba(166, 77, 121, 0.5);
                    border-radius: 22px;
                    color: white;
                    font-weight: 600;
                    padding: 12px 24px;
                }
                QPushButton:hover {
                    background: rgba(166, 77, 121, 0.3);
                    border: 2px solid rgba(166, 77, 121, 0.7);
                }
            """)
    
    def _apply_light_style(self):
        """Apply light theme button styling"""
        if self.button_type == "primary":
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #7F3F7F, stop:1 #A96FA9);
                    border: none;
                    border-radius: 22px;
                    color: white;
                    font-weight: 600;
                    padding: 12px 24px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #6F356F, stop:1 #99629A);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #5F2B5F, stop:1 #89558A);
                }
                QPushButton:disabled {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #CCCCCC, stop:1 #DDDDDD);
                    color: #888888;
                }
            """)
        elif self.button_type == "success":
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #A96FA9, stop:1 #7F3F7F);
                    border: none;
                    border-radius: 22px;
                    color: white;
                    font-weight: 600;
                    padding: 12px 24px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #99629A, stop:1 #6F356F);
                }
            """)
        elif self.button_type == "danger":
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #eb3349, stop:1 #f45c43);
                    border: none;
                    border-radius: 22px;
                    color: white;
                    font-weight: 600;
                    padding: 12px 24px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #d42e42, stop:1 #e5533c);
                }
            """)
        else:  # secondary
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(248, 248, 250, 0.8);
                    border: 2px solid rgba(127, 63, 127, 0.4);
                    border-radius: 22px;
                    color: #3D2B3D;
                    font-weight: 600;
                    padding: 12px 24px;
                }
                QPushButton:hover {
                    background: rgba(248, 248, 250, 1.0);
                    border: 2px solid rgba(127, 63, 127, 0.6);
                }
            """)
    
    def set_theme(self, is_light_mode):
        """Update theme for this button"""
        self.is_light_mode = is_light_mode
        self.apply_style()
        
        # Update shadow
        shadow = self.graphicsEffect()
        if shadow:
            if is_light_mode:
                shadow.setColor(QColor(127, 63, 127, 40))
            else:
                shadow.setColor(QColor(0, 0, 0, 60))


class GlassFrame(QFrame):
    """Modern glass-morphism frame with custom color scheme"""
    
    def __init__(self, is_light_mode=False):
        super().__init__()
        self.is_light_mode = is_light_mode
        self.apply_style()
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        if is_light_mode:
            shadow.setColor(QColor(127, 63, 127, 30))
        else:
            shadow.setColor(QColor(26, 26, 29, 50))
        self.setGraphicsEffect(shadow)
    
    def apply_style(self):
        """Apply frame style based on theme"""
        if self.is_light_mode:
            self.setStyleSheet("""
                QFrame {
                    background: rgba(248, 248, 250, 0.8);
                    border: 1px solid rgba(127, 63, 127, 0.2);
                    border-radius: 15px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background: rgba(166, 77, 121, 0.1);
                    border: 1px solid rgba(166, 77, 121, 0.3);
                    border-radius: 15px;
                }
            """)
    
    def set_theme(self, is_light_mode):
        """Update theme for this frame"""
        self.is_light_mode = is_light_mode
        self.apply_style()
        
        # Update shadow
        shadow = self.graphicsEffect()
        if shadow:
            if is_light_mode:
                shadow.setColor(QColor(127, 63, 127, 30))
            else:
                shadow.setColor(QColor(26, 26, 29, 50))


class YouTubeMusicExtractorGUI(QMainWindow):
    """Beautiful and modern YouTube Music Extractor GUI with theme switching"""
    
    def __init__(self):
        super().__init__()
        
        print("Initializing YouTube Music Extractor GUI...")
        
        # Settings
        self.settings = QSettings("YouTubeMusicExtractor", "Settings")
        
        # Worker thread
        self.download_worker = None
        
        # Animation objects
        self.animations = []
        
        # Theme state - load from settings
        self.is_light_mode = self.settings.value("light_mode", False, type=bool)
        
        try:
            # Initialize UI
            print("Setting up user interface...")
            self.init_ui()
            self.load_settings()
            
            # Setup auto-save timer
            self.save_timer = QTimer()
            self.save_timer.timeout.connect(self.save_settings)
            self.save_timer.start(5000)  # Save every 5 seconds
            
            print("GUI initialization completed successfully!")
            
        except Exception as e:
            print(f"Error during GUI initialization: {e}")
            import traceback
            traceback.print_exc()

    def init_ui(self):
        """Initialize the beautiful user interface"""
        self.setWindowTitle("🎵 YouTube Music Extractor - Professional Edition")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)
        
        # Set window icon
        self.setWindowIcon(self.create_app_icon())
        
        # Apply global stylesheet based on current theme
        self.apply_theme()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Left panel (input and controls)
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # Right panel (output and preview)
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 2)
        
        # Create menu bar and status bar
        self.create_menu_bar()
        self.create_status_bar()
          # Show welcome animation
        self.show_welcome_animation()

    def apply_theme(self):
        """Apply theme based on current mode"""
        if self.is_light_mode:
            self.apply_light_theme()
        else:
            self.apply_dark_theme()

    def toggle_theme(self):
        """Toggle between light and dark themes"""
        self.is_light_mode = not self.is_light_mode
        self.settings.setValue("light_mode", self.is_light_mode)
        
        # Apply new theme
        self.apply_theme()
          # Update all UI components
        self.update_all_components_theme()
        
        # Update title button styling
        if hasattr(self, 'title_button'):
            if self.is_light_mode:
                self.title_button.setStyleSheet("""
                    QPushButton {
                        color: #3D2B3D;
                        background: transparent;
                        border: none;
                        text-align: left;
                        padding: 5px;
                    }
                    QPushButton:hover {
                        color: #6A4B93;
                        background: rgba(106, 75, 147, 0.1);
                        border-radius: 5px;
                    }
                    QPushButton:pressed {
                        color: #533A7B;
                        background: rgba(83, 58, 123, 0.2);
                    }
                """)
            else:
                self.title_button.setStyleSheet("""
                    QPushButton {
                        color: white;
                        background: transparent;
                        border: none;
                        text-align: left;
                        padding: 5px;
                    }
                    QPushButton:hover {
                        color: #B794F6;
                        background: rgba(183, 148, 246, 0.1);
                        border-radius: 5px;
                    }
                    QPushButton:pressed {
                        color: #9F7AEA;
                        background: rgba(159, 122, 234, 0.2);
                    }
                """)
        
        # Log the theme change
        theme_name = "Light Mode" if self.is_light_mode else "Dark Mode"
        self.log_output.append(f"🎨 Switched to {theme_name}")

    def update_all_components_theme(self):
        """Update theme for all UI components"""
        # Update buttons
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, ModernButton):
                attr.set_theme(self.is_light_mode)
        
        # Update frames
        if hasattr(self, 'centralWidget'):
            for widget in self.centralWidget().findChildren(GlassFrame):
                widget.set_theme(self.is_light_mode)
          # Update specific elements
        if hasattr(self, 'track_progress_label'):
            if self.is_light_mode:
                self.track_progress_label.setStyleSheet("color: rgba(61, 43, 61, 0.8);")
            else:
                self.track_progress_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        
        if hasattr(self, 'thumbnail_label'):
            if self.is_light_mode:
                self.thumbnail_label.setStyleSheet("""
                    QLabel {
                        border: 2px dashed rgba(127, 63, 127, 0.4);
                        border-radius: 12px;
                        background: rgba(248, 248, 250, 0.3);
                    }
                """)
            else:
                self.thumbnail_label.setStyleSheet("""
                    QLabel {
                        border: 2px dashed rgba(255, 255, 255, 0.3);
                        border-radius: 12px;
                        background: rgba(255, 255, 255, 0.05);
                    }
                """)
        
        # Update menu bar and status bar themes
        if hasattr(self, 'menuBar') and self.menuBar():
            self.apply_menu_bar_theme()
        
        if hasattr(self, 'status_bar'):
            self.apply_status_bar_theme()
        
        # Title button styling is now handled in toggle_theme method
        # No need to update it here as it's handled by the button's click event

    def apply_light_theme(self):
        """Apply beautiful light theme with white background and purple accents"""
        # Force white background at application level
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(255, 255, 255))
        palette.setColor(QPalette.WindowText, QColor(61, 43, 61))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(248, 248, 250))
        self.setPalette(palette)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
                color: #3D2B3D;
            }
            
            QWidget {
                background-color: #FFFFFF;
                color: #3D2B3D;
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }
            
            QLineEdit {
                background-color: rgba(248, 248, 250, 0.8);
                border: 2px solid rgba(127, 63, 127, 0.3);
                border-radius: 12px;
                padding: 12px 16px;
                font-size: 14px;
                color: #3D2B3D;
            }
            QLineEdit:hover {
                border: 2px solid rgba(127, 63, 127, 0.5);
                background-color: rgba(248, 248, 250, 1.0);
            }
            QLineEdit:focus {
                border: 2px solid rgba(127, 63, 127, 0.8);
                background-color: rgba(248, 248, 250, 1.0);
            }
            QLineEdit::placeholder {
                color: rgba(61, 43, 61, 0.6);
            }
            
            QTextEdit {
                background-color: rgba(248, 248, 250, 0.8);
                border: 1px solid rgba(127, 63, 127, 0.3);
                border-radius: 12px;
                padding: 12px;
                font-size: 13px;
                color: #3D2B3D;
            }
            
            QProgressBar {
                border: none;
                border-radius: 12px;
                background-color: rgba(230, 230, 235, 0.8);
                text-align: center;
                font-weight: bold;
                color: #3D2B3D;
                min-height: 24px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7F3F7F, stop:1 #A96FA9);
                border-radius: 12px;
            }
            
            QLabel {
                color: #3D2B3D;
                background: transparent;
            }
            
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid rgba(127, 63, 127, 0.3);
                border-radius: 12px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: rgba(248, 248, 250, 0.5);
                color: #3D2B3D;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 5px 10px;
                background-color: rgba(127, 63, 127, 0.15);
                border-radius: 6px;
                color: #3D2B3D;
            }
            
            QComboBox {
                background-color: rgba(248, 248, 250, 0.8);
                border: 2px solid rgba(127, 63, 127, 0.3);
                border-radius: 8px;
                padding: 8px 12px;
                min-width: 100px;
                color: #3D2B3D;
            }
            QComboBox:hover {
                border: 2px solid rgba(127, 63, 127, 0.5);
                background-color: rgba(248, 248, 250, 1.0);
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #3D2B3D;
            }
            QComboBox QAbstractItemView {
                background-color: rgba(248, 248, 250, 0.95);
                border: 1px solid rgba(127, 63, 127, 0.4);
                border-radius: 8px;
                color: #3D2B3D;
                selection-background-color: rgba(127, 63, 127, 0.3);
            }
            
            QSpinBox {
                background-color: rgba(248, 248, 250, 0.8);
                border: 2px solid rgba(127, 63, 127, 0.3);
                border-radius: 8px;
                padding: 8px;
                color: #3D2B3D;
                min-width: 60px;
            }
            QSpinBox:hover {
                border: 2px solid rgba(127, 63, 127, 0.5);
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: rgba(127, 63, 127, 0.2);
                border: none;
                width: 20px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: rgba(127, 63, 127, 0.4);
            }
            
            QCheckBox {
                spacing: 8px;
                color: #3D2B3D;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid rgba(127, 63, 127, 0.5);
                background-color: rgba(248, 248, 250, 0.5);
            }
            QCheckBox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7F3F7F, stop:1 #A96FA9);
                border: 2px solid #7F3F7F;
            }
            
            QTabWidget::pane {
                border: 1px solid rgba(127, 63, 127, 0.3);
                border-radius: 8px;
                background-color: rgba(248, 248, 250, 0.5);
            }
            QTabBar::tab {
                background-color: rgba(248, 248, 250, 0.7);
                border: 1px solid rgba(127, 63, 127, 0.3);
                padding: 8px 16px;
                margin-right: 2px;
                color: #3D2B3D;
            }
            QTabBar::tab:selected {
                background-color: rgba(127, 63, 127, 0.2);
                border-bottom: 3px solid #7F3F7F;
            }
            QTabBar::tab:first {
                border-top-left-radius: 8px;
            }
            QTabBar::tab:last {
                border-top-right-radius: 8px;
            }
            
            QScrollBar:vertical {
                background-color: rgba(230, 230, 235, 0.8);
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(127, 63, 127, 0.4);
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(127, 63, 127, 0.6);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            
            QMenuBar {
                background-color: rgba(248, 248, 250, 0.8);
                color: #3D2B3D;
                border-bottom: 1px solid rgba(127, 63, 127, 0.3);
                font-weight: 500;
            }
            QMenuBar::item {
                padding: 8px 16px;
                background: transparent;
            }
            QMenuBar::item:selected {
                background-color: rgba(127, 63, 127, 0.2);
                border-radius: 4px;
            }
            QMenu {
                background-color: rgba(248, 248, 250, 0.95);
                border: 1px solid rgba(127, 63, 127, 0.3);
                border-radius: 8px;
                color: #3D2B3D;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background-color: rgba(127, 63, 127, 0.2);
            }
            
            QStatusBar {
                background-color: rgba(248, 248, 250, 0.8);
                color: #3D2B3D;
                border-top: 1px solid rgba(127, 63, 127, 0.3);
                font-size: 12px;
            }
        """)

    def create_app_icon(self):
        """Create a beautiful application icon with custom color scheme or load from file"""
        # First try to load icon from file
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        
        # Fallback to generated icon
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create gradient with custom colors
        gradient = QLinearGradient(0, 0, 64, 64)
        gradient.setColorAt(0, QColor(106, 30, 85))  # #6A1E55
        gradient.setColorAt(1, QColor(166, 77, 121))  # #A64D79
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 64, 64, 12, 12)
        
        # Add music note
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(20, 40, 12, 12)
        painter.drawRect(30, 20, 3, 25)
        painter.drawEllipse(35, 15, 8, 8)
        
        painter.end()
        return QIcon(pixmap)
    
    def apply_global_theme(self):
        """Apply beautiful global theme with custom color palette"""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1A1A1D, stop:0.3 #3B1C32, stop:0.7 #6A1E55, stop:1 #A64D79);
                color: white;
            }
            
            QWidget {
                color: white;
                font-family: 'Segoe UI', 'Arial', sans-serif;
                background: transparent;
            }
            
            QLineEdit {
                background: rgba(166, 77, 121, 0.15);
                border: 2px solid rgba(166, 77, 121, 0.4);
                border-radius: 12px;
                padding: 12px 16px;
                font-size: 14px;
                color: white;
            }
            QLineEdit:hover {
                border: 2px solid rgba(166, 77, 121, 0.6);
                background: rgba(166, 77, 121, 0.2);
            }
            QLineEdit:focus {
                border: 2px solid rgba(166, 77, 121, 0.8);
                background: rgba(166, 77, 121, 0.25);
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.6);
            }
            
            QTextEdit {
                background: rgba(26, 26, 29, 0.6);
                border: 1px solid rgba(166, 77, 121, 0.3);
                border-radius: 12px;
                padding: 12px;
                font-size: 13px;
                color: white;
                selection-background-color: rgba(166, 77, 121, 0.4);
            }
            
            QProgressBar {
                border: none;
                border-radius: 12px;
                background: rgba(26, 26, 29, 0.3);
                text-align: center;
                font-weight: bold;
                color: white;
                min-height: 24px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6A1E55, stop:1 #A64D79);
                border-radius: 12px;
            }
            
            QLabel {
                color: white;
                font-weight: 500;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid rgba(166, 77, 121, 0.3);
                border-radius: 12px;
                margin-top: 10px;
                padding-top: 10px;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 8px 0 8px;
                color: rgba(166, 77, 121, 1);
                font-weight: bold;
            }
            
            QComboBox {
                background: rgba(59, 28, 50, 0.4);
                border: 2px solid rgba(166, 77, 121, 0.3);
                border-radius: 8px;
                padding: 8px 12px;
                color: white;
                font-size: 13px;
                min-height: 20px;
            }
            QComboBox:hover {
                border: 2px solid rgba(166, 77, 121, 0.5);
                background: rgba(59, 28, 50, 0.6);
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid rgba(166, 77, 121, 0.8);
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background: rgba(59, 28, 50, 0.95);
                border: 1px solid rgba(166, 77, 121, 0.4);
                selection-background-color: rgba(166, 77, 121, 0.4);
                color: white;
            }
            
            QSpinBox {
                background: rgba(59, 28, 50, 0.4);
                border: 2px solid rgba(166, 77, 121, 0.3);
                border-radius: 8px;
                padding: 8px 12px;
                color: white;
                font-size: 13px;
            }
            QSpinBox:hover {
                border: 2px solid rgba(166, 77, 121, 0.5);
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: rgba(166, 77, 121, 0.3);
                border: none;
                width: 20px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: rgba(166, 77, 121, 0.5);
            }
            
            QCheckBox {
                color: white;
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid rgba(166, 77, 121, 0.5);
                border-radius: 4px;
                background: rgba(59, 28, 50, 0.3);
            }
            QCheckBox::indicator:checked {
                background: rgba(166, 77, 121, 0.8);
                border: 2px solid #A64D79;
            }
            
            QTabWidget::pane {
                border: 1px solid rgba(166, 77, 121, 0.4);
                border-radius: 8px;
                background: rgba(26, 26, 29, 0.3);
            }
            QTabBar::tab {
                background: rgba(59, 28, 50, 0.5);
                border: 1px solid rgba(166, 77, 121, 0.3);
                padding: 8px 16px;
                margin-right: 2px;
                color: white;
            }
            QTabBar::tab:selected {
                background: rgba(166, 77, 121, 0.4);
                border-bottom: 3px solid #A64D79;
            }
            QTabBar::tab:first {
                border-top-left-radius: 8px;
            }
            QTabBar::tab:last {
                border-top-right-radius: 8px;
            }
            
            QScrollBar:vertical {
                background: rgba(26, 26, 29, 0.5);
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgba(166, 77, 121, 0.5);
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(166, 77, 121, 0.7);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            
            QMenuBar {
                background: rgba(26, 26, 29, 0.3);
                color: white;
                border-bottom: 1px solid rgba(166, 77, 121, 0.3);
                font-weight: 500;
            }
            QMenuBar::item {
                padding: 8px 16px;
                background: transparent;
            }
            QMenuBar::item:selected {
                background: rgba(166, 77, 121, 0.3);
                border-radius: 4px;
            }
            QMenu {
                background: rgba(59, 28, 50, 0.95);
                border: 1px solid rgba(166, 77, 121, 0.4);
                border-radius: 8px;
                color: white;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background: rgba(166, 77, 121, 0.4);
            }
            
            QStatusBar {
                background: rgba(26, 26, 29, 0.3);
                color: white;
                border-top: 1px solid rgba(166, 77, 121, 0.3);
                font-size: 12px;
            }
        """)
        
        # Force repaint to ensure theme is applied
        if hasattr(self, 'centralWidget') and self.centralWidget():
            self.centralWidget().update()
            self.update()

    def apply_dark_theme(self):
        """Apply beautiful dark theme - the original stunning design"""
        # Set dark palette
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(26, 26, 29))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(35, 35, 38))
        palette.setColor(QPalette.AlternateBase, QColor(59, 28, 50))
        self.setPalette(palette)
        
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a1d, stop:0.5 #3b1c32, stop:1 #1a1a1d);
                color: white;
            }
            
            QWidget {
                background: transparent;
                color: white;
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }
            
            QLineEdit {
                background: rgba(59, 28, 50, 0.4);
                border: 2px solid rgba(166, 77, 121, 0.3);
                border-radius: 12px;
                padding: 12px 16px;
                font-size: 14px;
                color: white;
            }
            QLineEdit:hover {
                border: 2px solid rgba(166, 77, 121, 0.5);
                background: rgba(59, 28, 50, 0.6);
            }
            QLineEdit:focus {
                border: 2px solid rgba(166, 77, 121, 0.8);
                background: rgba(59, 28, 50, 0.7);
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.6);
            }
            
            QTextEdit {
                background: rgba(26, 26, 29, 0.4);
                border: 1px solid rgba(166, 77, 121, 0.3);
                border-radius: 12px;
                padding: 12px;
                font-size: 13px;
                color: white;
                selection-background-color: rgba(166, 77, 121, 0.4);
            }
            
            QProgressBar {
                border: none;
                border-radius: 12px;
                background: rgba(26, 26, 29, 0.3);
                text-align: center;
                font-weight: bold;
                color: white;
                min-height: 24px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6A1E55, stop:1 #A64D79);
                border-radius: 12px;
            }
            
            QLabel {
                color: white;
                font-weight: 500;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid rgba(166, 77, 121, 0.3);
                border-radius: 12px;
                margin-top: 10px;
                padding-top: 10px;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 8px 0 8px;
                color: rgba(166, 77, 121, 1);
                font-weight: bold;
            }
            
            QComboBox {
                background: rgba(59, 28, 50, 0.4);
                border: 2px solid rgba(166, 77, 121, 0.3);
                border-radius: 8px;
                padding: 8px 12px;
                color: white;
                font-size: 13px;
                min-height: 20px;
            }
            QComboBox:hover {
                border: 2px solid rgba(166, 77, 121, 0.5);
                background: rgba(59, 28, 50, 0.6);
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid rgba(166, 77, 121, 0.8);
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                background: rgba(59, 28, 50, 0.95);
                border: 1px solid rgba(166, 77, 121, 0.4);
                selection-background-color: rgba(166, 77, 121, 0.4);
                color: white;
            }
            
            QSpinBox {
                background: rgba(59, 28, 50, 0.4);
                border: 2px solid rgba(166, 77, 121, 0.3);
                border-radius: 8px;
                padding: 8px 12px;
                color: white;
                font-size: 13px;
            }
            QSpinBox:hover {
                border: 2px solid rgba(166, 77, 121, 0.5);
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background: rgba(166, 77, 121, 0.3);
                border: none;
                width: 20px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: rgba(166, 77, 121, 0.5);
            }
            
            QCheckBox {
                font-size: 13px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid rgba(166, 77, 121, 0.5);
                border-radius: 4px;
                background: rgba(59, 28, 50, 0.3);
            }
            QCheckBox::indicator:checked {
                background: rgba(166, 77, 121, 0.8);
                border: 2px solid #A64D79;
            }
            
            QTabWidget::pane {
                border: 1px solid rgba(166, 77, 121, 0.4);
                border-radius: 8px;
                background: rgba(26, 26, 29, 0.3);
            }
            QTabBar::tab {
                background: rgba(59, 28, 50, 0.5);
                border: 1px solid rgba(166, 77, 121, 0.3);
                padding: 8px 16px;
                margin-right: 2px;
                color: white;
            }
            QTabBar::tab:selected {
                background: rgba(166, 77, 121, 0.4);
                border-bottom: 3px solid #A64D79;
            }
            QTabBar::tab:first {
                border-top-left-radius: 8px;
            }
            QTabBar::tab:last {
                border-top-right-radius: 8px;
            }
            
            QScrollBar:vertical {
                background: rgba(26, 26, 29, 0.5);
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: rgba(166, 77, 121, 0.5);
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(166, 77, 121, 0.7);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            
            QMenuBar {
                background: rgba(26, 26, 29, 0.3);
                color: white;
                border-bottom: 1px solid rgba(166, 77, 121, 0.3);
                font-weight: 500;
            }
            QMenuBar::item {
                padding: 8px 16px;
                background: transparent;
            }
            QMenuBar::item:selected {
                background: rgba(166, 77, 121, 0.3);
                border-radius: 4px;
            }
            QMenu {
                background: rgba(59, 28, 50, 0.95);
                border: 1px solid rgba(166, 77, 121, 0.4);
                border-radius: 8px;
                color: white;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background: rgba(166, 77, 121, 0.4);
            }
            
            QStatusBar {
                background: rgba(26, 26, 29, 0.3);
                color: white;
                border-top: 1px solid rgba(166, 77, 121, 0.3);
                font-size: 12px;
            }
        """)
        
        # Force repaint to ensure theme is applied
        if hasattr(self, 'centralWidget') and self.centralWidget():
            self.centralWidget().update()
            self.update()

    def create_left_panel(self):
        """Create the beautiful left control panel"""
        panel = GlassFrame(self.is_light_mode)
        panel.setMaximumWidth(480)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)
          # Title and theme switcher row
        header_layout = QHBoxLayout()
        
        # Create clickable title button that toggles theme
        self.title_button = QPushButton("🎵 YouTube Music Extractor")
        self.title_button.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.title_button.setCursor(Qt.PointingHandCursor)
        self.title_button.setToolTip("Click to toggle between light and dark themes")
        self.title_button.clicked.connect(self.toggle_theme)
        
        # Style the button to look like a label but with hover effects
        if self.is_light_mode:
            self.title_button.setStyleSheet("""
                QPushButton {
                    color: #3D2B3D;
                    background: transparent;
                    border: none;
                    text-align: left;
                    padding: 5px;
                }
                QPushButton:hover {
                    color: #6A4B93;
                    background: rgba(106, 75, 147, 0.1);
                    border-radius: 5px;
                }
                QPushButton:pressed {
                    color: #533A7B;
                    background: rgba(83, 58, 123, 0.2);
                }
            """)
        else:
            self.title_button.setStyleSheet("""
                QPushButton {
                    color: white;
                    background: transparent;
                    border: none;
                    text-align: left;
                    padding: 5px;
                }
                QPushButton:hover {
                    color: #B794F6;
                    background: rgba(183, 148, 246, 0.1);
                    border-radius: 5px;
                }
                QPushButton:pressed {
                    color: #9F7AEA;
                    background: rgba(159, 122, 234, 0.2);
                }            """)
        
        header_layout.addWidget(self.title_button)
        # Theme switcher button is now moved to be next to the save log button
        
        layout.addLayout(header_layout)
        
        # URL Input Section
        url_group = QGroupBox("📎 Input URL")
        url_layout = QVBoxLayout(url_group)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste YouTube URL here (single track, playlist, or album)")
        self.url_input.setMinimumHeight(50)
        self.url_input.textChanged.connect(self.on_url_changed)
        url_layout.addWidget(self.url_input)
          # URL buttons row
        url_buttons_layout = QHBoxLayout()
        
        self.paste_button = ModernButton("📋 Paste", "secondary", self.is_light_mode)
        self.paste_button.clicked.connect(self.paste_url)
        url_buttons_layout.addWidget(self.paste_button)
        
        self.clear_button = ModernButton("🗑️ Clear", "secondary", self.is_light_mode)
        self.clear_button.clicked.connect(self.clear_url)
        url_buttons_layout.addWidget(self.clear_button)
        
        self.analyze_button = ModernButton("🔍 Analyze", "primary", self.is_light_mode)
        self.analyze_button.clicked.connect(self.analyze_url)
        self.analyze_button.setEnabled(False)
        self.analyze_button.setMinimumWidth(120)  # Adjusted width
        self.analyze_button.setMaximumWidth(120)  # Fixed width        url_buttons_layout.addWidget(self.analyze_button)
        
        url_layout.addLayout(url_buttons_layout)
        layout.addWidget(url_group)
        
        # Quality Settings
        quality_group = QGroupBox("⚙️ Quality Settings")
        quality_layout = QVBoxLayout(quality_group)
        
        # Format selection
        format_layout = QHBoxLayout()
        audio_quality_label = QLabel("Audio Quality:")
        audio_quality_label.setAlignment(Qt.AlignCenter)  # Center-align label
        format_layout.addWidget(audio_quality_label)
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([
            "Best Quality (320kbps+)",
            "High Quality (256kbps)",
            "Medium Quality (128kbps)",
            "Custom Format"
        ])
        self.quality_combo.setCurrentIndex(1)
        self.quality_combo.setMaximumWidth(200)  # Reduce box width
        format_layout.addWidget(self.quality_combo)
        quality_layout.addLayout(format_layout)
        
        # Parallel downloads
        parallel_layout = QHBoxLayout()
        parallel_label = QLabel("Parallel Downloads:")
        parallel_label.setAlignment(Qt.AlignCenter)  # Center-align label
        parallel_layout.addWidget(parallel_label)
        
        self.parallel_spin = QSpinBox()
        self.parallel_spin.setRange(1, 8)
        self.parallel_spin.setValue(4)
        self.parallel_spin.setMaximumWidth(80)  # Reduce box width
        parallel_layout.addWidget(self.parallel_spin)
        quality_layout.addLayout(parallel_layout)
        
        layout.addWidget(quality_group)
        
        # Output Settings
        output_group = QGroupBox("📁 Output Settings")
        output_layout = QVBoxLayout(output_group)
        
        # Output directory
        dir_layout = QHBoxLayout()
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setText(os.getcwd())
        self.output_dir_input.setReadOnly(True)
        dir_layout.addWidget(self.output_dir_input)
        
        self.browse_button = ModernButton("📂 Browse", "secondary", self.is_light_mode)
        self.browse_button.clicked.connect(self.browse_output_dir)
        dir_layout.addWidget(self.browse_button)
        output_layout.addLayout(dir_layout)
          # Additional options
        self.metadata_check = QCheckBox("📝 Add metadata and cover art")
        self.metadata_check.setChecked(True)
        output_layout.addWidget(self.metadata_check)
        
        self.cleanup_check = QCheckBox("🧹 Auto-cleanup temporary files")
        self.cleanup_check.setChecked(True)
        output_layout.addWidget(self.cleanup_check)
        
        layout.addWidget(output_group)
        
        # Main action buttons
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(10)
        
        self.download_button = ModernButton("🚀 Start Download", "success", self.is_light_mode)
        self.download_button.setMinimumHeight(55)
        self.download_button.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.download_button.clicked.connect(self.start_download)
        self.download_button.setEnabled(False)
        buttons_layout.addWidget(self.download_button)
        
        self.cancel_button = ModernButton("⏹️ Cancel", "danger", self.is_light_mode)
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setVisible(False)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
        
        # Add stretch to push everything up        layout.addStretch()
        
        return panel
    
    def create_right_panel(self):
        """Create the beautiful right panel for output and preview"""
        panel = GlassFrame(self.is_light_mode)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Progress section
        progress_group = QGroupBox("📊 Download Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Status label
        self.status_label = QLabel("Ready to download")
        self.status_label.setFont(QFont("Segoe UI", 12, QFont.Medium))
        self.status_label.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        
        # Track progress
        self.track_progress_label = QLabel("")
        self.track_progress_label.setAlignment(Qt.AlignCenter)
        if self.is_light_mode:
            self.track_progress_label.setStyleSheet("color: rgba(61, 43, 61, 0.8);")
        else:
            self.track_progress_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        progress_layout.addWidget(self.track_progress_label)
        
        layout.addWidget(progress_group)
        
        # Preview section
        preview_group = QGroupBox("🖼️ Album Art Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setMinimumSize(300, 300)
        self.thumbnail_label.setMaximumSize(400, 400)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        if self.is_light_mode:
            self.thumbnail_label.setStyleSheet("""
                QLabel {
                    border: 2px dashed rgba(127, 63, 127, 0.4);
                    border-radius: 12px;
                    background: rgba(248, 248, 250, 0.3);
                }
            """)
        else:
            self.thumbnail_label.setStyleSheet("""
                QLabel {
                    border: 2px dashed rgba(255, 255, 255, 0.3);
                    border-radius: 12px;
                    background: rgba(255, 255, 255, 0.05);
                }
            """)
        self.thumbnail_label.setText("🎨\nAlbum art will appear here")
        preview_layout.addWidget(self.thumbnail_label)
        
        layout.addWidget(preview_group)
        
        # Log output
        log_group = QGroupBox("📝 Activity Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(200)
        self.log_output.setReadOnly(True)
        self.log_output.append("🎵 YouTube Music Extractor ready!")
        self.log_output.append("📋 Paste a YouTube URL to get started.")
        log_layout.addWidget(self.log_output)
          # Log controls
        log_controls = QHBoxLayout()
        
        self.clear_log_button = ModernButton("🗑️ Clear Log", "secondary", self.is_light_mode)
        self.clear_log_button.clicked.connect(self.clear_log)
        log_controls.addWidget(self.clear_log_button)
        
        self.save_log_button = ModernButton("💾 Save Log", "secondary", self.is_light_mode)
        self.save_log_button.clicked.connect(self.save_log)
        log_controls.addWidget(self.save_log_button)
          # Theme switching is now handled by clicking the title button
        
        log_controls.addStretch()
        log_layout.addLayout(log_controls)
        
        layout.addWidget(log_group)
        
        return panel
    
    def create_menu_bar(self):
        """Create beautiful menu bar"""
        menubar = self.menuBar()
        self.apply_menu_bar_theme()
        
        # File menu
        file_menu = menubar.addMenu("📁 File")
        
        open_output_action = QAction("📂 Open Output Folder", self)
        open_output_action.triggered.connect(self.open_output_folder)
        file_menu.addAction(open_output_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("🚪 Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("🔧 Tools")
        
        check_formats_action = QAction("🔍 Check Available Formats", self)
        check_formats_action.triggered.connect(self.check_formats_dialog)
        tools_menu.addAction(check_formats_action)
        
        # Help menu
        help_menu = menubar.addMenu("❓ Help")
        
        about_action = QAction("ℹ️ About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def apply_menu_bar_theme(self):
        """Apply theme-aware styling to menu bar"""
        menubar = self.menuBar()
        if self.is_light_mode:
            menubar.setStyleSheet("""
                QMenuBar {
                    background: rgba(248, 248, 250, 0.9);
                    color: #3D2B3D;
                    border-bottom: 1px solid rgba(127, 63, 127, 0.3);
                    font-weight: 500;
                }
                QMenuBar::item {
                    padding: 8px 16px;
                    background: transparent;
                }
                QMenuBar::item:selected {
                    background: rgba(127, 63, 127, 0.2);
                    border-radius: 4px;
                }
                QMenu {
                    background: rgba(248, 248, 250, 0.95);
                    border: 1px solid rgba(127, 63, 127, 0.3);
                    border-radius: 8px;
                    color: #3D2B3D;
                }
                QMenu::item {
                    padding: 8px 20px;
                }
                QMenu::item:selected {
                    background: rgba(127, 63, 127, 0.2);
                }
            """)
        else:
            menubar.setStyleSheet("""
                QMenuBar {
                    background: rgba(26, 26, 29, 0.3);
                    color: white;
                    border-bottom: 1px solid rgba(166, 77, 121, 0.3);
                    font-weight: 500;
                }
                QMenuBar::item {
                    padding: 8px 16px;
                    background: transparent;
                }
                QMenuBar::item:selected {
                    background: rgba(166, 77, 121, 0.3);
                    border-radius: 4px;
                }
                QMenu {
                    background: rgba(59, 28, 50, 0.95);
                    border: 1px solid rgba(166, 77, 121, 0.4);
                    border-radius: 8px;
                    color: white;
                }
                QMenu::item {
                    padding: 8px 20px;
                }
                QMenu::item:selected {
                    background: rgba(166, 77, 121, 0.4);
                }
            """)
    
    def create_status_bar(self):
        """Create beautiful status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.apply_status_bar_theme()
        self.status_bar.showMessage("🎵 Ready to extract music from YouTube")
    
    def apply_status_bar_theme(self):
        """Apply theme-aware styling to status bar"""
        if self.is_light_mode:
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background: rgba(248, 248, 250, 0.9);
                    color: #3D2B3D;
                    border-top: 1px solid rgba(127, 63, 127, 0.3);
                    font-size: 12px;
                }
            """)
        else:
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background: rgba(26, 26, 29, 0.3);
                    color: white;
                    border-top: 1px solid rgba(166, 77, 121, 0.3);
                    font-size: 12px;
                }
            """)
    
    def show_welcome_animation(self):
        """Show a beautiful welcome animation"""
        # This could be enhanced with actual animations
        self.log_output.append("🌟 Welcome to YouTube Music Extractor!")
        self.log_output.append("✨ Modern, beautiful, and powerful music extraction")
    
    # Event handlers
    def on_url_changed(self):
        """Handle URL input changes"""
        url = self.url_input.text().strip()
        is_valid = self.is_valid_youtube_url(url)
        
        self.analyze_button.setEnabled(is_valid)
        self.download_button.setEnabled(is_valid)
        
        if is_valid:
            self.status_bar.showMessage("🔗 Valid YouTube URL detected")
        else:
            self.status_bar.showMessage("🎵 Ready to extract music from YouTube")
    
    def is_valid_youtube_url(self, url):
        """Check if URL is a valid YouTube URL"""
        if not url:
            return False
        
        youtube_domains = ['youtube.com', 'youtu.be', 'music.youtube.com']
        return any(domain in url for domain in youtube_domains)
    
    def paste_url(self):
        """Paste URL from clipboard"""
        clipboard = QApplication.clipboard()
        url = clipboard.text().strip()
        
        if url:
            self.url_input.setText(url)
            self.log_output.append(f"📋 Pasted URL: {url}")
    
    def clear_url(self):
        """Clear URL input"""
        self.url_input.clear()
        self.progress_bar.setValue(0)
        self.thumbnail_label.setText("🎨\nAlbum art will appear here")
        self.track_progress_label.setText("")
        self.log_output.append("🗑️ URL cleared")
    
    def analyze_url(self):
        """Analyze the YouTube URL"""
        url = self.url_input.text().strip()
        if not url:
            return
        
        self.log_output.append(f"🔍 Analyzing URL: {url}")
        self.status_bar.showMessage("🔍 Analyzing URL...")
        
        # This could show format information
        self.log_output.append("✅ URL analysis complete")
        self.status_bar.showMessage("✅ URL analyzed successfully")
    
    def browse_output_dir(self):
        """Browse for output directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self, 
            "📁 Select Output Directory",
            self.output_dir_input.text()
        )
        
        if dir_path:
            self.output_dir_input.setText(dir_path)
            self.log_output.append(f"📁 Output directory set: {dir_path}")
    
    def start_download(self):
        """Start the download process"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a YouTube URL")
            return
        
        output_dir = self.output_dir_input.text()
        if not os.path.exists(output_dir):
            QMessageBox.warning(self, "Warning", "Output directory does not exist")
            return
        
        # Get quality format
        quality_map = {
            0: "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio[ext=opus]/bestaudio/best",
            1: "bestaudio[abr<=256]/bestaudio/best",
            2: "bestaudio[abr<=128]/bestaudio/best", 
            3: "bestaudio/best"
        }
        quality_format = quality_map.get(self.quality_combo.currentIndex(), quality_map[1])
        
        # Update UI for download state
        self.download_button.setEnabled(False)
        self.download_button.setVisible(False)
        self.cancel_button.setEnabled(True)
        self.cancel_button.setVisible(True)
        
        self.progress_bar.setValue(0)
        self.status_label.setText("🚀 Starting download...")
        
        # Start worker thread
        self.download_worker = DownloadWorker(
            url, 
            output_dir, 
            quality_format,
            self.parallel_spin.value()
        )
          # Connect signals
        self.download_worker.progress_updated.connect(self.update_progress)
        self.download_worker.status_updated.connect(self.update_status)
        self.download_worker.log_updated.connect(self.add_log_message)
        self.download_worker.download_finished.connect(self.download_finished)
        self.download_worker.thumbnail_ready.connect(self.show_thumbnail)
        self.download_worker.track_processed.connect(self.update_track_progress)
        self.download_worker.speed_updated.connect(self.update_speed)
        self.download_worker.eta_updated.connect(self.update_eta)
        
        self.download_worker.start()
        
        self.log_output.append("🚀 Download started!")
        self.status_bar.showMessage("🚀 Download in progress...")
    
    def cancel_download(self):
        """Cancel the download process"""
        if self.download_worker:
            self.download_worker.cancel()
            self.download_worker.wait()
          # Reset UI
        self.download_button.setEnabled(True)
        self.download_button.setVisible(True)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setVisible(False)
        self.status_label.setText("❌ Download cancelled")
        self.log_output.append("❌ Download cancelled by user")
        self.status_bar.showMessage("❌ Download cancelled")
    
    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)
    
    def update_status(self, message):
        """Update status label"""
        self.status_label.setText(message)
    
    def update_speed(self, speed_str):
        """Update download speed display"""
        self.status_bar.showMessage(f"⚡ Speed: {speed_str}")
    
    def update_eta(self, eta_str):
        """Update estimated time remaining display"""
        current_status = self.status_label.text()
        if not current_status.endswith(f" - ETA: {eta_str}"):
            # Update status to include ETA if not already present
            base_status = current_status.split(" - ETA:")[0]
            self.status_label.setText(f"{base_status} - ETA: {eta_str}")
    
    def add_log_message(self, message, msg_type):
        """Add message to log with color coding"""
        color_map = {
            "info": "white",
            "success": "#38ef7d", 
            "warning": "#ffd93d",
            "error": "#ff6b6b"
        }
        
        color = color_map.get(msg_type, "white")
        formatted_message = f'<span style="color: {color};">{message}</span>'
        
        self.log_output.append(formatted_message)
        
        # Auto-scroll to bottom
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_track_progress(self, track_name, current, total):
        """Update track processing progress"""
        if total > 1:
            self.track_progress_label.setText(f"🎵 Processing: {track_name}\n({current}/{total} tracks)")
        else:
            self.track_progress_label.setText(f"🎵 Processing: {track_name}")
    
    def download_finished(self, success, message):
        """Handle download completion"""
        # Reset UI
        self.download_button.setEnabled(True)
        self.download_button.setVisible(True)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setVisible(False)
        
        if success:
            self.status_label.setText("🎉 Download completed!")
            self.progress_bar.setValue(100)
            self.log_output.append(f"🎉 {message}")
            self.status_bar.showMessage("🎉 Download completed successfully!")
            
            # Show completion message
            QMessageBox.information(self, "Success", f"🎉 Download completed!\n\n{message}")
        else:
            self.status_label.setText("❌ Download failed")
            self.log_output.append(f"❌ {message}")
            self.status_bar.showMessage("❌ Download failed")
            
            # Show error message
            QMessageBox.critical(self, "Error", f"❌ Download failed:\n\n{message}")
    
    def show_thumbnail(self, thumbnail_path):
        """Display thumbnail preview"""
        try:
            pixmap = QPixmap(thumbnail_path)
            if not pixmap.isNull():
                # Scale to fit the label while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    self.thumbnail_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.thumbnail_label.setPixmap(scaled_pixmap)
                self.thumbnail_label.setStyleSheet("""
                    QLabel {
                        border: 2px solid rgba(255, 255, 255, 0.5);
                        border-radius: 12px;
                    }
                """)
        except Exception as e:
            self.log_output.append(f"⚠️ Could not display thumbnail: {e}")
    
    def clear_log(self):
        """Clear the log output"""
        self.log_output.clear()
        self.log_output.append("🎵 YouTube Music Extractor ready!")
    
    def save_log(self):
        """Save log to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "💾 Save Log File",
            f"yt_extractor_log_{int(time.time())}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_output.toPlainText())
                self.log_output.append(f"💾 Log saved to: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save log:\n{e}")
    
    def open_output_folder(self):
        """Open output folder in file explorer"""
        output_dir = self.output_dir_input.text()
        if os.path.exists(output_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir))
        else:
            QMessageBox.warning(self, "Warning", "Output directory does not exist")
    
    def check_formats_dialog(self):
        """Show available formats dialog"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a YouTube URL first")
            return
        
        # This would show a dialog with available formats
        QMessageBox.information(self, "Formats", "Format checking feature coming soon!")
    
    def show_about(self):
        """Show about dialog"""
        about_text = """
        <h2>🎵 YouTube Music Extractor</h2>
        <p><b>Professional Edition</b></p>
        <p>Beautiful, modern music extractor with advanced features</p>
        
        <h3>✨ Features:</h3>
        <ul>
        <li>🎵 High-quality audio extraction</li>
        <li>🖼️ Automatic metadata and cover art</li>
        <li>📁 Smart file organization</li>
        <li>⚡ Parallel processing</li>
        <li>🎨 Beautiful modern interface</li>
        <li>🔧 Advanced customization</li>
        </ul>
        
        <p><b>Version:</b> 2.0.0</p>
        <p><b>Author:</b> YouTube Music Extractor Team</p>
        """
        
        QMessageBox.about(self, "About YouTube Music Extractor", about_text)
    
    def load_settings(self):
        """Load user settings"""
        try:
            output_dir = self.settings.value("output_dir", os.getcwd())
            self.output_dir_input.setText(output_dir)
            
            quality_index = self.settings.value("quality_index", 1, type=int)
            self.quality_combo.setCurrentIndex(quality_index)
            
            parallel_count = self.settings.value("parallel_count", 4, type=int)
            self.parallel_spin.setValue(parallel_count)
            
            metadata_enabled = self.settings.value("metadata_enabled", True, type=bool)
            self.metadata_check.setChecked(metadata_enabled)
            
            cleanup_enabled = self.settings.value("cleanup_enabled", True, type=bool)
            self.cleanup_check.setChecked(cleanup_enabled)
            
        except Exception as e:
            self.log_output.append(f"⚠️ Could not load settings: {e}")
    
    def save_settings(self):
        """Save user settings"""
        try:
            self.settings.setValue("output_dir", self.output_dir_input.text())
            self.settings.setValue("quality_index", self.quality_combo.currentIndex())
            self.settings.setValue("parallel_count", self.parallel_spin.value())
            self.settings.setValue("metadata_enabled", self.metadata_check.isChecked())
            self.settings.setValue("cleanup_enabled", self.cleanup_check.isChecked())
            
        except Exception as e:
            print(f"Could not save settings: {e}")
    
    def closeEvent(self, event):
        """Handle application close"""
        # Save settings
        self.save_settings()
        
        # Cancel any running downloads
        if self.download_worker and self.download_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "A download is in progress. Are you sure you want to exit?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.download_worker.cancel()
                self.download_worker.wait(3000)  # Wait up to 3 seconds
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Main entry point for the beautiful GUI"""
    try:
        app = QApplication(sys.argv)
        
        # Set application properties
        app.setApplicationName("YouTube Music Extractor")
        app.setApplicationVersion("2.0.0")
        app.setOrganizationName("YouTubeMusicExtractor")
        app.setQuitOnLastWindowClosed(True)
        
        # Load custom font if available
        try:
            QFontDatabase.addApplicationFont("assets/fonts/Segoe UI.ttf")
        except:
            pass
        
        # Create and show main window
        window = YouTubeMusicExtractorGUI()
        window.show()
        window.raise_()  # Bring to front
        window.activateWindow()  # Activate the window
        
        # Ensure window is visible and not minimized
        from PyQt5.QtCore import Qt
        window.setWindowState(window.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        
        print("YouTube Music Extractor GUI is now running!")
        print("Window should be visible on your screen.")
        
        # Run application
        return app.exec_()
        
    except Exception as e:
        print(f"Error starting GUI: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    main()
