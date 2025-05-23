import yt_dlp
import os
import requests
from moviepy import AudioFileClip
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC, TIT2, TALB, TPE1, TCON
from PIL import Image
import io
try:
    url = input("Enter the YouTube URL: ")
except KeyboardInterrupt:
    print("\nExiting...")
    exit()

# Directory to save
output_template = "%(title)s.%(ext)s"

# Step 1: Download best audio without conversion
ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': output_template,
    'writeinfojson': True,
    'writethumbnail': True,
    # No postprocessors to let us handle conversion with moviepy
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    result = ydl.extract_info(url, download=True)

# Step 2: Get file info and metadata
title = result.get("title")
artist = result.get("artist") or result.get("uploader")
album = result.get("album") or result.get("title")
genre = result.get("genre") or "YouTube Music"
thumbnail_url = result.get("thumbnail")

# Get the downloaded file name
original_filename = f"{title}.{result.get('ext')}"
output_filename = f"{title}.m4a"  # Target format is m4a

# Download the thumbnail - with better error handling
img_path = "cover.jpg"
jpg_path = "cover_jpg.jpg"  # Always ensure we have a JPG version
print(f"Downloading thumbnail from {thumbnail_url}")
try:
    response = requests.get(thumbnail_url, timeout=10)
    response.raise_for_status()
    img_data = response.content
    with open(img_path, "wb") as handler:
        handler.write(img_data)
    print(f"Thumbnail downloaded successfully to {img_path}, size: {len(img_data)} bytes")
    
    # Convert to JPG and crop to 1:1 aspect ratio
    try:
        img = Image.open(io.BytesIO(img_data))
        
        # Crop to 1:1 square ratio (centered)
        width, height = img.size
        if width != height:
            print(f"Cropping image from {width}x{height} to 1:1 ratio")
            # Determine the crop dimensions
            if width > height:
                # Landscape image
                left = (width - height) // 2
                top = 0
                right = left + height
                bottom = height
            else:
                # Portrait image
                left = 0
                top = (height - width) // 2
                right = width
                bottom = top + width
            
            # Crop and convert to RGB
            img = img.crop((left, top, right, bottom))
            print(f"Cropped to square: {img.size[0]}x{img.size[1]}")
        
        # Resize for better VLC compatibility (300-500px is optimal for VLC)
        target_size = 500
        if max(img.size) > target_size:
            img.thumbnail((target_size, target_size), Image.LANCZOS)
            print(f"Resized to: {img.size[0]}x{img.size[1]} for better VLC compatibility")
            
        # Convert to RGB mode for JPG
        img = img.convert('RGB')
        
        # Save as JPG (this ensures compatibility)
        img.save(jpg_path, "JPEG", quality=95)  # Higher quality for VLC
        print(f"Created square JPG version of cover art: {jpg_path}")
        img_path = jpg_path  # Use the JPG version
    except Exception as e:
        print(f"Error processing image: {e}")
except Exception as e:
    print(f"Error downloading thumbnail: {e}")
    # Try to use the thumbnail downloaded by yt-dlp instead
    possible_thumbnails = [f"{title}.jpg", f"{title}.webp", f"{title}.png"]
    for possible_thumb in possible_thumbnails:
        if os.path.exists(possible_thumb):
            img_path = possible_thumb
            print(f"Using yt-dlp generated thumbnail: {img_path}")
            
            # Convert to JPG if not already and crop to 1:1
            try:
                img = Image.open(img_path)
                
                # Crop to 1:1 square ratio (centered)
                width, height = img.size
                if width != height:
                    print(f"Cropping image from {width}x{height} to 1:1 ratio")
                    # Determine the crop dimensions
                    if width > height:
                        # Landscape image
                        left = (width - height) // 2
                        top = 0
                        right = left + height
                        bottom = height
                    else:
                        # Portrait image
                        left = 0
                        top = (height - width) // 2
                        right = width
                        bottom = top + width
                    
                    # Crop and convert to RGB
                    img = img.crop((left, top, right, bottom))
                    print(f"Cropped to square: {img.size[0]}x{img.size[1]}")
                
                # Resize for better VLC compatibility
                target_size = 500
                if max(img.size) > target_size:
                    img.thumbnail((target_size, target_size), Image.LANCZOS)
                    print(f"Resized to {img.size[0]}x{img.size[1]} for better VLC compatibility")
                
                # Convert to RGB mode for JPG
                img = img.convert('RGB')
                img.save(jpg_path, "JPEG", quality=95)
                print(f"Converted {img_path} to square JPG format: {jpg_path}")
                img_path = jpg_path
            except Exception as e:
                print(f"Error converting thumbnail: {e}")
            break
    else:
        print("No thumbnail found")

# Step 3: Convert audio to m4a using moviepy
print(f"Converting {original_filename} to {output_filename}...")
try:
    audio_clip = AudioFileClip(original_filename)
    audio_clip.write_audiofile(output_filename, codec='aac', bitrate='256k')
    audio_clip.close()
    
    # Delete the original file after successful conversion
    os.remove(original_filename)
    print(f"Converted to {output_filename} successfully")
except Exception as e:
    print(f"Error converting audio: {e}")
    output_filename = original_filename  # Fall back to original file

# Step 4: Tag the audio file with metadata
print("Adding metadata and cover art...")
try:
    audio = MP4(output_filename)
    
    # Clear any existing metadata tags first (helps with VLC)
    for key in list(audio.keys()):
        if key.startswith('\xa9') or key in ['covr']:
            del audio[key]
    
    audio['\xa9nam'] = title  # Title
    audio['\xa9ART'] = artist  # Artist
    audio['\xa9alb'] = album  # Album
    audio['\xa9gen'] = genre  # Genre
    
    # VLC also likes these additional tags
    audio['©day'] = str(result.get('upload_date', ''))[:4]  # Year
    
    # Add cover art with better error handling
    if os.path.exists(img_path):
        print(f"Reading cover art from {img_path}")
        with open(img_path, "rb") as f:
            cover_data = f.read()
        print(f"Cover data size: {len(cover_data)} bytes")
        
        # Always use JPEG format for better compatibility
        image_format = MP4Cover.FORMAT_JPEG
        
        try:
            audio['covr'] = [MP4Cover(cover_data, imageformat=image_format)]
            print("Cover art added to MP4 container")
        except Exception as e:
            print(f"Error adding cover to MP4: {e}")
    else:
        print(f"Cover art file not found: {img_path}")
    
    audio.save()
    print("Metadata and cover art saved successfully")
    
    # For extra VLC compatibility - save a copy of the cover beside the audio file
    # VLC often looks for external artwork with the same name
    folder_art_path = os.path.splitext(output_filename)[0] + ".jpg"
    if os.path.exists(img_path):
        import shutil
        shutil.copy2(img_path, folder_art_path)
        print(f"Created external cover art file: {folder_art_path} (helps with VLC)")
        
except Exception as e:
    print(f"Error adding metadata: {e}")

# Improved cleanup to remove ALL temporary files
print("Cleaning up temporary files...")
try:
    # Files to clean up with exact names we know
    temp_files = [
        img_path, 
        jpg_path, 
        "cover.jpg",
        original_filename     # Original audio file (backup check)
    ]
    
    # Keep track of how many files were deleted
    deleted_count = 0
    
    # Don't delete these files
    keep_files = [
        output_filename,    # The final M4A file
        folder_art_path     # The external artwork for VLC
    ]
    
    # Delete all temporary files that we named explicitly
    for temp_file in temp_files:
        if os.path.exists(temp_file) and temp_file not in keep_files:
            os.remove(temp_file)
            print(f"Removed temporary file: {temp_file}")
            deleted_count += 1
    
    # Find and delete any yt-dlp generated files that match our title
    # These might have spaces and special characters in them
    files_in_dir = os.listdir('.')
    for file in files_in_dir:
        # If the file begins with the video title but isn't our final m4a file or external artwork
        if (file.startswith(title) and 
            file != output_filename and 
            file != os.path.basename(folder_art_path)):
            # Keep the external jpg file for VLC that we created
            if file.endswith('.jpg') and os.path.abspath(file) == os.path.abspath(folder_art_path):
                continue
            os.remove(file)
            print(f"Removed yt-dlp generated file: {file}")
            deleted_count += 1
    
    print(f"Cleanup complete: {deleted_count} temporary files removed")
except Exception as e:
    print(f"Error during cleanup: {e}")

print("✅ Downloaded with full metadata and album art!")
