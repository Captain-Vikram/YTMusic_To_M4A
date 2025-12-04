import yt_dlp
import os
import requests
import shutil
import threading
import time
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC, TIT2, TALB, TPE1, TCON
from PIL import Image
import io

def sanitize_filename(filename):
    """Make filenames safe for Windows and other filesystems.

    This replaces reserved characters, normalizes smart quotes, removes
    control characters and strips trailing spaces/dots.
    """
    if not filename:
        return 'Unknown'
    s = str(filename)
    smart_quotes = '“”‘’«»'
    for ch in smart_quotes:
        s = s.replace(ch, '"')
    invalid_chars = '<>:"/\\|?*'
    for ch in invalid_chars:
        s = s.replace(ch, '_')
    s = ''.join(c if ord(c) >= 32 else '_' for c in s)
    s = s.strip()
    while s.endswith('.') or s.endswith(' '):
        s = s[:-1]
    while '__' in s:
        s = s.replace('__', '_')
    if not s:
        return 'Unknown'
    return s

def process_cover_art(img_path, jpg_path):
    """Process cover art: crop to square and resize for VLC compatibility"""
    try:
        img = Image.open(img_path)
        
        # Crop to 1:1 square ratio (centered)
        width, height = img.size
        if width != height:
            print(f"Cropping image from {width}x{height} to 1:1 ratio")
            if width > height:
                left = (width - height) // 2
                top = 0
                right = left + height
                bottom = height
            else:
                left = 0
                top = (height - width) // 2
                right = width
                bottom = top + width
            
            img = img.crop((left, top, right, bottom))
            print(f"Cropped to square: {img.size[0]}x{img.size[1]}")
        
        # Resize for better VLC compatibility
        target_size = 500
        if max(img.size) > target_size:
            img.thumbnail((target_size, target_size), Image.LANCZOS)
            print(f"Resized to: {img.size[0]}x{img.size[1]} for better VLC compatibility")
            
        # Convert to RGB mode for JPG
        img = img.convert('RGB')
        img.save(jpg_path, "JPEG", quality=95)
        print(f"Created square JPG version of cover art: {jpg_path}")
        return jpg_path
    except Exception as e:
        print(f"Error processing image: {e}")
        return img_path


def _find_ffmpeg():
    """Locate ffmpeg executable using IMAGEIO_FFMPEG_EXE or PATH."""
    ff = os.environ.get('IMAGEIO_FFMPEG_EXE')
    if ff and os.path.exists(ff):
        return ff
    return shutil.which('ffmpeg')


def ffmpeg_convert(input_path, output_path, bitrate='256k'):
    """Convert input audio/video to M4A using ffmpeg subprocess.

    Raises RuntimeError on failure.
    """
    ff = _find_ffmpeg()
    if not ff:
        raise RuntimeError('ffmpeg executable not found')

    cmd = [ff, '-y', '-i', input_path, '-c:a', 'aac', '-b:a', bitrate, output_path]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        stderr = proc.stderr.decode(errors='ignore')
        raise RuntimeError(f'ffmpeg conversion failed: {stderr}')
    return True

def process_single_track(entry, album_folder, cover_art_path, album_title, track_num=None, total_tracks=None):
    """Process a single track from an album or a standalone song"""
    try:
        title = sanitize_filename(entry.get("title", "Unknown"))
        artist = entry.get("artist") or entry.get("uploader", "Unknown Artist")
        genre = entry.get("genre") or "YouTube Music"
        
        track_info = f"Track {track_num}/{total_tracks}: {title}" if track_num else title
        print(f"🎵 Starting {track_info}")
        
        # Find the downloaded audio file - be more flexible with filename matching - UPDATED TO HANDLE MP4
        possible_extensions = ['m4a', 'webm', 'mp4', 'opus', 'aac', 'mp3']  # Added MP4 and other formats
        original_filename = None
        
        # Search for files that start with the title (handles slight filename variations)
        search_locations = ['.']
        if album_folder:
            search_locations.append(album_folder)
        
        for location in search_locations:
            if not os.path.exists(location):
                continue
                
            for file in os.listdir(location):
                # Check if file starts with our title and has a valid audio extension
                file_base, file_ext = os.path.splitext(file)
                if (file_base.startswith(title) or title.startswith(file_base)) and file_ext[1:] in possible_extensions:
                    original_filename = os.path.join(location, file)
                    print(f"🔍 Found audio file: {original_filename}")
                    break
            
            if original_filename:
                break
        
        if not original_filename:
            print(f"⚠️ Warning: Could not find audio file for {title}")
            # List available files for debugging
            print("Available files in current directory:")
            for file in os.listdir('.'):
                print(f"  - {file}")
            if album_folder and os.path.exists(album_folder):
                print(f"Available files in {album_folder}:")
                for file in os.listdir(album_folder):
                    print(f"  - {file}")
            return False
        
        # Ensure album folder exists
        if album_folder and not os.path.exists(album_folder):
            os.makedirs(album_folder, exist_ok=True)
            
        # Set output path - always in album folder if it's an album
        # Use the original filename's base name to maintain consistency
        original_base = os.path.splitext(os.path.basename(original_filename))[0]
        if album_folder:
            output_filename = os.path.join(album_folder, f"{original_base}.m4a")
        else:
            output_filename = f"{original_base}.m4a"
        
        print(f"📁 Input: {original_filename}")
        print(f"📁 Output: {output_filename}")
        
        # Convert audio to m4a using ffmpeg subprocess (fallbacks to keeping original)
        print(f"🔄 Converting {track_info}...")
        try:
            # If already M4A, keep as-is
            if original_filename.lower().endswith('.m4a'):
                print(f"✅ File is already M4A format, no conversion needed")
                output_filename = original_filename
            else:
                # Attempt ffmpeg conversion
                try:
                    ffmpeg_convert(original_filename, output_filename, bitrate='256k')
                    # Remove original if conversion produced a different file
                    try:
                        if os.path.exists(original_filename) and os.path.abspath(original_filename) != os.path.abspath(output_filename):
                            os.remove(original_filename)
                            print(f"🗑️ Removed original file: {original_filename}")
                    except Exception:
                        pass
                except Exception as conv_e:
                    # Conversion failed — re-raise to be handled by outer except
                    raise conv_e

            print(f"✅ Converted {track_info}")
        except Exception as e:
            print(f"❌ Error converting {track_info}: {e}")
            # If conversion failed, check if we can work with the original file
            if original_filename.lower().endswith('.m4a') and os.path.exists(original_filename):
                output_filename = original_filename
                print(f"✅ Using original M4A file: {output_filename}")
            else:
                # Move original file to album folder if conversion failed
                if album_folder and original_filename != output_filename:
                    try:
                        target_path = os.path.join(album_folder, os.path.basename(original_filename))
                        if original_filename != target_path:
                            shutil.move(original_filename, target_path)
                        output_filename = target_path
                    except Exception as move_e:
                        print(f"⚠️ Could not move {original_filename}: {move_e}")
                        output_filename = original_filename

                # Skip metadata for non-M4A files
                if not output_filename.lower().endswith('.m4a'):
                    print(f"⚠️ Skipping metadata for non-M4A file: {output_filename}")
                    return True  # Still consider it successful since we have the audio file

        # Verify the output file exists before adding metadata
        if not os.path.exists(output_filename):
            print(f"⚠️ Output file does not exist after conversion: {output_filename}")
            print(f"🔍 Checking if original file still exists: {os.path.exists(original_filename)}")
            # List files in the album folder for debugging
            if album_folder and os.path.exists(album_folder):
                print(f"📂 Files in {album_folder}:")
                for file in os.listdir(album_folder):
                    print(f"  - {file}")
            return False
        
        # Add metadata and cover art
        print(f"🏷️ Adding metadata to {track_info}...")
        try:
            # Verify it's an M4A file by checking extension
            if not output_filename.lower().endswith('.m4a'):
                print(f"⚠️ File is not M4A format: {output_filename}")
                return False
            
            audio = MP4(output_filename)
            
            # Clear existing metadata
            for key in list(audio.keys()):
                if key.startswith('\xa9') or key in ['covr']:
                    del audio[key]
            
            audio['\xa9nam'] = [original_base]  # Use original filename for title
            audio['\xa9ART'] = [artist]  # Artist
            audio['\xa9alb'] = [album_title]  # Album
            audio['\xa9gen'] = [genre]  # Genre
            
            # Add track number if available
            if track_num:
                audio['trkn'] = [(track_num, total_tracks or 0)]
            
            # Add year if available
            if 'upload_date' in entry:
                audio['©day'] = [str(entry.get('upload_date', ''))[:4]]
            
            # Add cover art
            if cover_art_path and os.path.exists(cover_art_path):
                with open(cover_art_path, "rb") as f:
                    cover_data = f.read()
                audio['covr'] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]
            
            audio.save()
            
            # Create external cover art for VLC compatibility
            folder_art_path = os.path.splitext(output_filename)[0] + ".jpg"
            if cover_art_path and os.path.exists(cover_art_path):
                shutil.copy2(cover_art_path, folder_art_path)
            
            print(f"✅ Metadata added to {track_info}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding metadata to {track_info}: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Fatal error processing {track_info if 'track_info' in locals() else 'track'}: {e}")
        return False

def main():
    """Entry point for the console script."""
    try:
        url = input("Enter the YouTube URL: ")
        
        # Ask if user wants to check available formats
        check_formats = input("Check available audio formats first? (y/n): ").lower().strip()
        if check_formats == 'y':
            check_available_formats(url)
            proceed = input("\nProceed with download? (y/n): ").lower().strip()
            if proceed != 'y':
                print("Download cancelled.")
                return
                
    except KeyboardInterrupt:
        print("\nExiting...")
        exit()

    # First, extract info to determine if it's a playlist/album
    print("Analyzing URL...")
    ydl_opts_info = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,  # Continue on errors during analysis
    }

    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            error_msg = str(e).lower()
            if 'video unavailable' in error_msg or 'private video' in error_msg:
                print(f"❌ Video unavailable: {e}")
                print("💡 This video is private, deleted, or not accessible.")
                print("💡 Please check the URL and try again with an accessible video or playlist.")
                exit()
            else:
                print(f"❌ Error extracting info: {e}")
                exit()
    
    # Check if info extraction was successful
    if not info:
        print("❌ Could not extract video information")
        print("💡 The video may be unavailable, private, or the URL may be incorrect.")
        exit()

    # Check if it's a playlist/album
    is_playlist = '_type' in info and info['_type'] == 'playlist'

    if is_playlist:
        print(f"🎵 Detected album/playlist: {info.get('title', 'Unknown Album')}")
        print(f"📀 Found {len(info.get('entries', []))} tracks")
        
        # Create album folder
        album_title = sanitize_filename(info.get('title', 'Unknown Album'))
        album_folder = album_title
        if not os.path.exists(album_folder):
            os.makedirs(album_folder)
            print(f"📁 Created album folder: {album_folder}")
        
        # Download all tracks directly to album folder
        output_template = os.path.join(album_folder, "%(title)s.%(ext)s")
    else:
        print(f"🎵 Detected single track: {info.get('title', 'Unknown')}")
        # Create folder for single track too for better organization
        track_title = sanitize_filename(info.get('title', 'Unknown'))
        album_folder = f"Single - {track_title}"
        album_title = track_title
        if not os.path.exists(album_folder):
            os.makedirs(album_folder)
            print(f"📁 Created track folder: {album_folder}")
        output_template = os.path.join(album_folder, "%(title)s.%(ext)s")

    # Download with yt-dlp - Enhanced for highest quality and maximum speed
    print("⬇️ Starting high-speed parallel download...")
    ydl_opts = {
        # Enhanced format selection for highest quality audio - FIXED TO EXTRACT AUDIO FROM VIDEO
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio[ext=opus]/bestaudio/best[height<=720]',
        'outtmpl': output_template,
        'writeinfojson': True,  # Enable to check quality info
        'writethumbnail': True,
        # Audio extraction settings - FORCE AUDIO EXTRACTION
        'extractaudio': True,  # Extract audio from video
        'audioformat': 'm4a',  # Convert to M4A format
        'audioquality': '256K',  # High quality audio
        # Add quality verification
        'extract_flat': False,
        'listformats': False,  # Set to True temporarily to see available formats
        'ignoreerrors': True,  # Continue on download errors
        'no_warnings': True,
        # Performance optimizations for faster downloads
        'concurrent_fragment_downloads': 8,  # Download fragments in parallel
        'fragment_retries': 3,  # Retry failed fragments
        'retries': 3,  # Retry failed downloads
        'socket_timeout': 30,  # Socket timeout in seconds
        'http_chunk_size': 10485760,  # 10MB chunks for faster download
        # Network optimizations
        'prefer_insecure': False,  # Use HTTPS when possible
        'geo_bypass': True,  # Bypass geographic restrictions
        'geo_bypass_country': None,  # Let yt-dlp choose best bypass
        # Connection optimizations
        'playlist_items': None,  # Download all items
        'playliststart': 1,  # Start from first item
        'playlistend': None,  # Download till end
        # Speed optimizations
        'simulate': False,  # Don't simulate, actually download
        'skip_download': False,  # Don't skip download
        'logtostderr': False,  # Don't log to stderr for cleaner output
    }

    # Optional: Print available formats for quality verification
    print("🔍 Checking available audio formats...")
    ydl_opts_check = {
        'listformats': True,
        'quiet': False,
    }
    
    # Uncomment these lines to see all available formats:
    # with yt_dlp.YoutubeDL(ydl_opts_check) as ydl_check:
    #     ydl_check.extract_info(url, download=False)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=True)
        
        # Check if result is valid
        if not result:
            print("❌ No content could be downloaded")
            exit()
        
        # For playlists, filter out failed entries
        if is_playlist and 'entries' in result:
            original_count = len(result.get('entries', []))
            # Filter out None entries (failed downloads)
            result['entries'] = [entry for entry in result.get('entries', []) if entry is not None]
            failed_count = original_count - len(result['entries'])
            
            if failed_count > 0:
                print(f"⚠️ {failed_count} tracks could not be downloaded (unavailable/private)")
            
            if not result['entries']:
                print("❌ No tracks in playlist are available for download")
                exit()
        
    except Exception as e:
        error_msg = str(e).lower()
        if 'video unavailable' in error_msg or 'private video' in error_msg:
            if is_playlist:
                print("⚠️ Some tracks in playlist are unavailable, continuing with available tracks...")
                # For playlists, try to continue with available tracks
                try:
                    # Re-extract with ignoreerrors to get partial results
                    ydl_opts['ignoreerrors'] = True
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        result = ydl.extract_info(url, download=True)
                    if result and result.get('entries'):
                        result['entries'] = [entry for entry in result.get('entries', []) if entry is not None]
                        if result['entries']:
                            print(f"✅ Downloaded {len(result['entries'])} available tracks")
                        else:
                            print("❌ No tracks in playlist are available")
                            exit()
                    else:
                        print("❌ Could not download any tracks from playlist")
                        exit()
                except Exception as retry_error:
                    print(f"❌ Playlist download failed: {retry_error}")
                    exit()
            else:
                # For single tracks, this is a fatal error
                print(f"❌ Video unavailable: {e}")
                print("This video is not available for download (private, deleted, or region-restricted)")
                exit()
        else:
            # Other types of errors
            print(f"❌ Download error: {e}")
            exit()
        
        # Check what format was actually downloaded
        if is_playlist:
            for entry in result.get('entries', []):
                if entry and 'format' in entry:
                    print(f"📊 Downloaded format for '{entry.get('title', 'Unknown')}': {entry.get('format_id', 'Unknown')} - {entry.get('ext', 'Unknown')} - {entry.get('abr', 'Unknown')}kbps")
        else:
            if 'format' in result:
                print(f"📊 Downloaded format: {result.get('format_id', 'Unknown')} - {result.get('ext', 'Unknown')} - {result.get('abr', 'Unknown')}kbps")
        
    print("✅ Download completed!")

    # Handle cover art download and processing
    print("🎨 Processing cover art...")
    cover_art_path = None

    if is_playlist:
        # For playlists, try to get album artwork
        playlist_title = sanitize_filename(result.get('title', 'Unknown Album'))
        possible_thumbnails = [
            os.path.join(album_folder, f"{playlist_title}.jpg"),
            os.path.join(album_folder, f"{playlist_title}.webp"), 
            os.path.join(album_folder, f"{playlist_title}.png"),
            f"{playlist_title}.jpg",  # Also check main directory
            f"{playlist_title}.webp", 
            f"{playlist_title}.png"
        ]
        
        # Try to download from thumbnail URL if available
        thumbnail_url = result.get("thumbnail")
        if thumbnail_url:
            print(f"📥 Downloading album artwork...")
            try:
                response = requests.get(thumbnail_url, timeout=10)
                response.raise_for_status()
                img_data = response.content
                temp_cover_path = "temp_cover.jpg"
                with open(temp_cover_path, "wb") as handler:
                    handler.write(img_data)
                
                cover_art_path = process_cover_art(temp_cover_path, os.path.join(album_folder, "cover.jpg"))
                if os.path.exists(temp_cover_path):
                    os.remove(temp_cover_path)
                print("✅ Album artwork processed")
            except Exception as e:
                print(f"❌ Error downloading album artwork: {e}")
        
        # If direct download failed, look for yt-dlp generated thumbnails
        if not cover_art_path:
            for possible_thumb in possible_thumbnails:
                if os.path.exists(possible_thumb):
                    print(f"📷 Using yt-dlp generated album artwork: {os.path.basename(possible_thumb)}")
                    cover_art_path = process_cover_art(possible_thumb, os.path.join(album_folder, "cover.jpg"))
                    break
        
        # Process tracks in parallel - Enhanced filtering to skip unavailable/private videos
        all_entries = result.get('entries', [])
        valid_entries = []
        skipped_count = 0
        
        for entry in all_entries:
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
                print(f"⚠️ Skipping unavailable track: {entry.get('title', 'Unknown')}")
                continue
            
            valid_entries.append(entry)
        
        entries = valid_entries
        total_tracks = len(entries)
        
        if skipped_count > 0:
            print(f"📋 Skipped {skipped_count} unavailable/private tracks")
        
        if not entries:
            print("❌ No valid tracks found to process")
            exit()
        
        if entries:
            print(f"\n🚀 Starting parallel processing of {total_tracks} tracks...")
            
            # Use ThreadPoolExecutor for parallel processing
            max_workers = min(8, total_tracks)  # Increase to 8 concurrent threads for faster processing
            successful_tracks = 0
            failed_tracks = 0
            
            # Progress tracking
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                print(f"⚡ Using {max_workers} parallel workers for maximum speed")
                
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
                
                # Process completed tasks with real-time progress
                for future in as_completed(future_to_track):
                    track_num, track_title = future_to_track[future]
                    try:
                        success = future.result()
                        if success:
                            successful_tracks += 1
                            print(f"✅ [{successful_tracks}/{total_tracks}] Track {track_num} completed: {track_title}")
                        else:
                            failed_tracks += 1
                            print(f"❌ [{failed_tracks} failed] Track {track_num} failed: {track_title}")
                        
                        # Calculate and show ETA
                        elapsed_time = time.time() - start_time
                        completed = successful_tracks + failed_tracks
                        if completed > 0:
                            avg_time_per_track = elapsed_time / completed
                            remaining_tracks = total_tracks - completed
                            eta_seconds = avg_time_per_track * remaining_tracks
                            eta_minutes = eta_seconds / 60
                            
                            if eta_minutes > 1:
                                print(f"⏱️ Progress: {completed}/{total_tracks} tracks | ETA: {eta_minutes:.1f} minutes")
                            else:
                                print(f"⏱️ Progress: {completed}/{total_tracks} tracks | ETA: {eta_seconds:.0f} seconds")
                    except Exception as e:
                        failed_tracks += 1
                        print(f"❌ Track {track_num} error: {track_title} - {str(e)}")
                        # Continue processing other tracks even if one fails
                        continue
            
            total_time = time.time() - start_time
            print(f"\n🎉 Parallel processing completed in {total_time:.1f} seconds!")
            print(f"📊 Results: {successful_tracks} successful, {failed_tracks} failed out of {total_tracks} tracks")
            print(f"⚡ Average time per track: {total_time/total_tracks:.1f} seconds")
        
    else:
        # Single track processing
        title = sanitize_filename(result.get("title", "Unknown"))
        thumbnail_url = result.get("thumbnail")
        
        # Download and process cover art
        if thumbnail_url:
            print(f"📥 Downloading thumbnail...")
            try:
                response = requests.get(thumbnail_url, timeout=10)
                response.raise_for_status()
                img_data = response.content
                temp_cover_path = "temp_cover.jpg"
                with open(temp_cover_path, "wb") as handler:
                    handler.write(img_data)
                
                # Save cover art to the single track folder, not main directory
                cover_art_path = process_cover_art(temp_cover_path, os.path.join(album_folder, "cover.jpg"))
                if os.path.exists(temp_cover_path):
                    os.remove(temp_cover_path)
                print("✅ Thumbnail processed")
            except Exception as e:
                print(f"❌ Error downloading thumbnail: {e}")
        
        # Look for yt-dlp generated thumbnails if direct download failed
        if not cover_art_path:
            # Check both main directory and album folder for thumbnails
            possible_thumbnails = [
                os.path.join(album_folder, f"{title}.jpg"),
                os.path.join(album_folder, f"{title}.webp"), 
                os.path.join(album_folder, f"{title}.png"),
                f"{title}.jpg",  # Also check main directory
                f"{title}.webp", 
                f"{title}.png"
            ]
            for possible_thumb in possible_thumbnails:
                if os.path.exists(possible_thumb):
                    print(f"📷 Using yt-dlp generated thumbnail: {os.path.basename(possible_thumb)}")
                    cover_art_path = process_cover_art(possible_thumb, os.path.join(album_folder, "cover.jpg"))
                    break
        
        # Process the single track - PASS album_folder instead of None
        print("\n🎵 Processing single track...")
        success = process_single_track(result, album_folder, cover_art_path, album_title)
        if success:
            print("✅ Single track processed successfully!")
        else:
            print("❌ Failed to process single track")

    # Cleanup temporary files
    print("\n🧹 Cleaning up temporary files...")

    def cleanup_directory(directory_path, is_main_dir=True):
        """Clean up temporary files in a specific directory"""
        deleted_count = 0
        
        try:
            if not os.path.exists(directory_path):
                return 0
                
            files_in_dir = os.listdir(directory_path)
            
            # File extensions to keep (project files) - only for main directory
            keep_extensions = {'.py', '.md', '.txt', '.json', '.gitignore'}
            
            # Specific important files to keep regardless of extension - only for main directory
            important_files = {'LICENSE', 'setup.py', 'requirements.txt', '.gitignore', 'config.py'}
            
            for file in files_in_dir:
                file_path = os.path.join(directory_path, file)
                
                # Skip directories
                if os.path.isdir(file_path):
                    continue
                
                # Get file extension
                _, ext = os.path.splitext(file)
                
                should_delete = False
                
                # In main directory - keep important project files
                if is_main_dir:
                    # Explicitly check for .gitignore
                    if file == '.gitignore' or file in important_files or ext.lower() in keep_extensions:
                        continue
                        
                    # Delete everything else in main directory (all temp files, audio files, images)
                    should_delete = True
                        
                else:
                    # In album/track folder - ONLY keep .m4a files and cover.jpg
                    if file.endswith('.m4a') or file == 'cover.jpg':
                        continue  # Keep these files
                    else:
                        should_delete = True  # Delete everything else
                
                if should_delete:
                    try:
                        os.remove(file_path)
                        print(f"🗑️ Removed: {file}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"⚠️ Could not remove {file}: {e}")
        
        except Exception as e:
            print(f"❌ Error cleaning directory {directory_path}: {e}")
        
        return deleted_count

    try:
        total_deleted = 0
        
        # Clean main directory
        print("🧹 Cleaning main directory...")
        total_deleted += cleanup_directory('.', is_main_dir=True)
        
        # Clean album/track folder if it exists
        if album_folder and os.path.exists(album_folder):
            print(f"🧹 Cleaning {album_folder} folder...")
            total_deleted += cleanup_directory(album_folder, is_main_dir=False)
        
        print(f"✅ Cleanup complete: {total_deleted} temporary files removed")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")

    print("\n" + "="*60)
    if is_playlist:
        print(f"🎉 Album '{album_title}' downloaded successfully!")
        print(f"📁 All tracks saved in folder: {album_folder}")
        print(f"🎵 {len([f for f in os.listdir(album_folder) if f.endswith('.m4a')])} M4A files ready")
    else:
        print("🎉 Single track downloaded with full metadata and album art!")

    print("🎵 All files ready for VLC and other media players!")
    print("="*60)
    print("\nThank you for using TrackOut! 🎶")

def check_available_formats(url):
    """Check and display available audio formats for quality verification"""
    print("🔍 Analyzing available audio formats...")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if '_type' in info and info['_type'] == 'playlist':
                # For playlists, check first entry
                entries = [entry for entry in info.get('entries', []) if entry]
                if entries:
                    formats = entries[0].get('formats', [])
                    title = entries[0].get('title', 'Unknown')
                else:
                    print("❌ No valid entries found in playlist")
                    return
            else:
                formats = info.get('formats', [])
                title = info.get('title', 'Unknown')
            
            # Filter audio-only formats
            audio_formats = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
            
            if audio_formats:
                print(f"\n🎵 Available audio formats for: {title}")
                print("-" * 80)
                print(f"{'Format ID':<12} {'Extension':<8} {'Quality':<15} {'Bitrate':<10} {'Codec':<10}")
                print("-" * 80)
                
                for fmt in sorted(audio_formats, key=lambda x: x.get('abr', 0) or 0, reverse=True):
                    format_id = fmt.get('format_id', 'Unknown')
                    ext = fmt.get('ext', 'Unknown')
                    quality = fmt.get('format_note', 'Unknown')
                    bitrate = f"{fmt.get('abr', 'Unknown')}kbps" if fmt.get('abr') else 'Unknown'
                    codec = fmt.get('acodec', 'Unknown')
                    
                    print(f"{format_id:<12} {ext:<8} {quality:<15} {bitrate:<10} {codec:<10}")
                print("-" * 80)
                
                # Find the best quality
                best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
                print(f"🏆 Highest quality: {best_audio.get('format_id')} - {best_audio.get('abr', 'Unknown')}kbps")
                
            else:
                print("❌ No audio-only formats found")
                
    except Exception as e:
        print(f"❌ Error checking formats: {e}")

if __name__ == "__main__":
    # When run directly, execute all the existing code
    main()
