import yt_dlp
import os
import requests
import shutil
import threading
import time
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from moviepy import AudioFileClip
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC, TIT2, TALB, TPE1, TCON
from PIL import Image
import io

def sanitize_filename(filename):
    """Remove or replace invalid characters for Windows filenames"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename.strip()

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

def process_single_track(entry, album_folder, cover_art_path, album_title, track_num=None, total_tracks=None):
    """Process a single track from an album or a standalone song"""
    try:
        title = sanitize_filename(entry.get("title", "Unknown"))
        artist = entry.get("artist") or entry.get("uploader", "Unknown Artist")
        genre = entry.get("genre") or "YouTube Music"
        
        track_info = f"Track {track_num}/{total_tracks}: {title}" if track_num else title
        print(f"🎵 Starting {track_info}")
        
        # Find the downloaded audio file
        possible_extensions = ['webm', 'mp4', 'm4a', 'opus']
        original_filename = None
        
        # Construct the expected filename based on download pattern
        expected_filename = None
        if album_folder:
            # For albums, file should be in album folder
            expected_filename = os.path.join(album_folder, f"{title}.webm")
        else:
            # For single tracks, file should be in main directory
            expected_filename = f"{title}.webm"
        
        # First try the expected location
        if os.path.exists(expected_filename):
            original_filename = expected_filename
        else:
            # Fallback: search in both locations with all extensions
            search_locations = ['.']
            if album_folder:
                search_locations.append(album_folder)
            
            for location in search_locations:
                for ext in possible_extensions:
                    potential_file = os.path.join(location, f"{title}.{ext}")
                    if os.path.exists(potential_file):
                        original_filename = potential_file
                        break
                if original_filename:
                    break
        
        if not original_filename:
            print(f"⚠️ Warning: Could not find audio file for {title}")
            return False
        
        # Ensure album folder exists
        if album_folder and not os.path.exists(album_folder):
            os.makedirs(album_folder, exist_ok=True)
          # Set output path - always in album folder if it's an album
        if album_folder:
            output_filename = os.path.join(album_folder, f"{title}.m4a")
        else:
            output_filename = f"{title}.m4a"
        
        # Convert audio to m4a
        print(f"🔄 Converting {track_info}...")
        try:
            audio_clip = AudioFileClip(original_filename)
            # Write audio file without verbose parameter for compatibility
            audio_clip.write_audiofile(
                output_filename, 
                codec='aac', 
                bitrate='256k', 
                logger=None
            )
            audio_clip.close()
              # Delete the original file after successful conversion
            if os.path.exists(original_filename):
                os.remove(original_filename)
            print(f"✅ Converted {track_info}")
        except Exception as e:
            print(f"❌ Error converting {track_info}: {e}")
            # If conversion failed, check if we can work with the original file
            if original_filename.lower().endswith('.m4a') and os.path.exists(original_filename):
                # It's already M4A, just move/copy it
                if album_folder and original_filename != output_filename:
                    try:
                        if os.path.dirname(original_filename) != album_folder:
                            shutil.move(original_filename, output_filename)
                        else:
                            output_filename = original_filename
                    except Exception as move_e:
                        print(f"⚠️ Could not move {original_filename}: {move_e}")
                        output_filename = original_filename
                else:
                    output_filename = original_filename
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
                        output_filename = original_filename                # Skip metadata for non-M4A files
                if not output_filename.lower().endswith('.m4a'):
                    print(f"⚠️ Skipping metadata for non-M4A file: {output_filename}")
                    return True  # Still consider it successful since we have the audio file
        
        # Add metadata and cover art
        print(f"🏷️ Adding metadata to {track_info}...")
        try:
            # Check if the file exists and is a valid M4A file
            if not os.path.exists(output_filename):
                print(f"⚠️ Output file does not exist: {output_filename}")
                return False
            
            # Verify it's an M4A file by checking extension
            if not output_filename.lower().endswith('.m4a'):
                print(f"⚠️ File is not M4A format: {output_filename}")
                return False
            
            audio = MP4(output_filename)
            
            # Clear existing metadata
            for key in list(audio.keys()):
                if key.startswith('\xa9') or key in ['covr']:
                    del audio[key]
            
            audio['\xa9nam'] = [title]  # Title
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
    except KeyboardInterrupt:
        print("\nExiting...")
        exit()

    # First, extract info to determine if it's a playlist/album
    print("Analyzing URL...")
    ydl_opts_info = {
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            print(f"Error extracting info: {e}")
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

    # Download with yt-dlp
    print("⬇️ Starting download...")
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'writeinfojson': False,  # Don't need JSON files
        'writethumbnail': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=True)

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
                
        # REMOVE THIS PART - it's trying to convert the album title as a file
        # Converting Album - Priceless.None to Album - Priceless.m4a...
        
        # Process tracks in parallel
        entries = [entry for entry in result.get('entries', []) if entry]  # Filter out None entries
        total_tracks = len(entries)
        
        if entries:
            print(f"\n🚀 Starting parallel processing of {total_tracks} tracks...")
            
            # Use ThreadPoolExecutor for parallel processing
            max_workers = min(4, total_tracks)  # Limit to 4 concurrent threads to avoid overwhelming the system
            successful_tracks = 0
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
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
                
                # Process completed tasks
                for future in as_completed(future_to_track):
                    track_num, track_title = future_to_track[future]
                    try:
                        success = future.result()
                        if success:
                            successful_tracks += 1
                        print(f"📊 Progress: {successful_tracks}/{total_tracks} tracks completed")
                    except Exception as e:
                        print(f"❌ Track {track_num} ({track_title}) failed: {e}")
            
            print(f"\n🎉 Parallel processing completed! {successful_tracks}/{total_tracks} tracks processed successfully")
        
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
    print("\nThank you for using YouTube Music Extractor! 🎶")

if __name__ == "__main__":
    # When run directly, execute all the existing code
    main()
