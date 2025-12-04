import yt_dlp
import os
import requests
import shutil
import threading
import time
import glob
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC, TIT2, TALB, TPE1, TCON
from PIL import Image
import io
import subprocess
import shutil
import os

def sanitize_filename(filename):
    """Make filenames safe for Windows and other filesystems.

    - Replace reserved characters with underscores
    - Normalize smart quotes and remove control characters
    - Strip trailing spaces and dots (invalid on Windows)
    - Collapse repeated underscores
    """
    if not filename:
        return 'Unknown'
    s = str(filename)
    # Normalize Unicode to NFKC so full-width punctuation (e.g. '？')
    # and other compatibility characters map to their ASCII forms
    # before we remove/replace invalid filesystem characters.
    try:
        s = unicodedata.normalize('NFKC', s)
    except Exception:
        pass
    # Normalize common smart quotes to straight quote then remove
    smart_quotes = '“”‘’«»'
    for ch in smart_quotes:
        s = s.replace(ch, '"')

    # Replace reserved filesystem characters
    invalid_chars = '<>:"/\\|?*'
    for ch in invalid_chars:
        s = s.replace(ch, '_')

    # Remove control characters
    s = ''.join(c if ord(c) >= 32 else '_' for c in s)

    # Trim and remove trailing dots/spaces (Windows limitation)
    s = s.strip()
    while s.endswith('.') or s.endswith(' '):
        s = s[:-1]

    # Collapse double underscores
    while '__' in s:
        s = s.replace('__', '_')

    if not s:
        return 'Unknown'
    return s

def normalize_name(value):
    """Create a simplified lowercase token for fuzzy filename matching."""
    if not value:
        return ''
    # Normalize to NFKD to split accents / full-width chars
    normalized = unicodedata.normalize('NFKD', value)
    # Encode to ASCII ignoring characters we cannot map (e.g., fancy quotes)
    ascii_only = normalized.encode('ascii', 'ignore').decode('ascii')
    # Keep alphanumeric characters only for robust comparison
    return ''.join(ch.lower() for ch in ascii_only if ch.isalnum())

def process_cover_art(img_path, jpg_path):
    """Process cover art: crop to square and resize for VLC compatibility"""
    try:
        img = Image.open(img_path)
        
        # Crop to 1:1 square ratio (centered)
        width, height = img.size
        if width != height:
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
        
        # Resize for better VLC compatibility
        target_size = 500
        if max(img.size) > target_size:
            img.thumbnail((target_size, target_size), Image.LANCZOS)
        
        # Convert to RGB mode for JPG
        img = img.convert('RGB')
        img.save(jpg_path, "JPEG", quality=95)
        return jpg_path
    except Exception:
        return img_path

def process_single_track(entry, album_folder, cover_art_path, album_title, track_num=None, total_tracks=None):
    """Process a single track from an album or a standalone song"""
    try:
        title = sanitize_filename(entry.get("title", "Unknown"))
        original_title = entry.get("title", "Unknown")  # Keep original for matching
        artist = entry.get("artist") or entry.get("uploader", "Unknown Artist")
        genre = entry.get("genre") or "YouTube Music"
        
        track_info = f"Track {track_num}/{total_tracks}: {title}" if track_num else title
        print(f"Starting {track_info}")
        
        possible_extensions = ['m4a', 'webm', 'mp4', 'opus', 'aac', 'mp3']
        original_filename = None
        search_locations = ['.']
        if album_folder:
            search_locations.append(album_folder)

        target_tokens = {
            normalize_name(original_title),
            normalize_name(title)
        }

        # Try to find the downloaded file - use flexible normalized matching
        for location in search_locations:
            if not os.path.exists(location):
                continue
            for file in os.listdir(location):
                file_base, file_ext = os.path.splitext(file)
                # Try multiple matching strategies
                if file_ext[1:] in possible_extensions:
                    base_norm = normalize_name(file_base)
                    # Check if filenames match (handling special characters)
                    if (file_base == original_title or  # Exact match with original title
                        file_base == title or  # Match with sanitized title
                        file_base.startswith(title[:20]) or  # Partial match (first 20 chars)
                        title.startswith(file_base[:20]) or
                        base_norm and base_norm in target_tokens):
                        original_filename = os.path.join(location, file)
                        print(f"Found file: {original_filename}")
                        break
            if original_filename:
                break

        if not original_filename:
            print(f"Could not find downloaded file for: {title}")
            # List files in album folder for debugging
            if album_folder and os.path.exists(album_folder):
                print(f"Files in {album_folder}: {os.listdir(album_folder)}")
            return False

        if album_folder and not os.path.exists(album_folder):
            os.makedirs(album_folder, exist_ok=True)
        
        original_base = os.path.splitext(os.path.basename(original_filename))[0]
        if album_folder:
            output_filename = os.path.join(album_folder, f"{original_base}.m4a")
        else:
            output_filename = f"{original_base}.m4a"

        # Detect existing .m4a files created by yt-dlp postprocessing and prefer them
        candidates = []
        try:
            if album_folder and os.path.exists(album_folder):
                for f in os.listdir(album_folder):
                    if f.lower().endswith('.m4a') and (f.startswith(original_base) or original_base.startswith(os.path.splitext(f)[0])):
                        candidates.append(os.path.join(album_folder, f))
            orig_dir = os.path.dirname(original_filename) or '.'
            if os.path.exists(orig_dir):
                for f in os.listdir(orig_dir):
                    if f.lower().endswith('.m4a') and (f.startswith(original_base) or original_base.startswith(os.path.splitext(f)[0])):
                        candidates.append(os.path.join(orig_dir, f))

            if candidates:
                candidates = sorted(candidates, key=lambda p: os.path.getsize(p) if os.path.exists(p) else 0, reverse=True)
                output_filename = candidates[0]
                print(f"Found existing m4a, skipping conversion: {output_filename}")
        except Exception:
            # ignore candidate scanning errors and continue to conversion/fallback
            pass

        # Prefer ffmpeg subprocess conversion (no heavy imports). If ffmpeg unavailable, fall back to MoviePy if present.
        def _find_ffmpeg():
            ff = os.environ.get('IMAGEIO_FFMPEG_EXE')
            if ff and os.path.exists(ff):
                return ff
            return shutil.which('ffmpeg')

        def _ffmpeg_convert(input_path, output_path, bitrate='256k'):
            ff = _find_ffmpeg()
            if not ff:
                raise RuntimeError('ffmpeg not found')
            cmd = [ff, '-y', '-i', input_path, '-c:a', 'aac', '-b:a', bitrate, output_path]
            creationflags = 0
            if os.name == 'nt' and hasattr(subprocess, 'HIGH_PRIORITY_CLASS'):
                creationflags = subprocess.HIGH_PRIORITY_CLASS
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.decode(errors='ignore'))
            return True

        try:
            if original_filename.lower().endswith('.m4a'):
                output_filename = original_filename
            else:
                # Try ffmpeg first
                try:
                    _ffmpeg_convert(original_filename, output_filename, bitrate='256k')
                    # remove original if different
                    try:
                        if os.path.exists(original_filename) and os.path.abspath(original_filename) != os.path.abspath(output_filename):
                            os.remove(original_filename)
                    except Exception:
                        pass
                    print(f"Converted {original_filename} -> {output_filename} (ffmpeg)")
                except Exception as ff_err:
                    # ffmpeg not available or failed — try MoviePy as a last resort
                    try:
                        from moviepy import AudioFileClip
                        if original_filename.lower().endswith('.mp4') or not original_filename.lower().endswith(('.webm', '.opus')):
                            audio_clip = AudioFileClip(original_filename)
                            audio_clip.write_audiofile(output_filename, codec='aac', bitrate='256k', logger=None, verbose=False, remove_temp=True, preset='fast', ffmpeg_params=['-threads', '0'])
                            audio_clip.close()
                            if os.path.exists(original_filename) and os.path.abspath(original_filename) != os.path.abspath(output_filename):
                                try:
                                    os.remove(original_filename)
                                except Exception:
                                    pass
                            print(f"Converted {original_filename} -> {output_filename} (moviepy)")
                        else:
                            output_filename = original_filename
                            print(f"Using original file without conversion: {output_filename}")
                    except Exception as mp_e:
                        # Last fallback: preserve original file
                        print(f"Conversion failed (ffmpeg/moviepy): {ff_err} | {mp_e}")
                        output_filename = original_filename
        except Exception as conv_err:
            # Catch-all for unexpected errors during conversion logic
            print(f"Conversion logic error: {conv_err}")
            output_filename = original_filename

        # After conversion or fallback, ensure output exists and write metadata
        try:
            if not os.path.exists(output_filename):
                print(f"Output file does not exist: {output_filename}")
                return False

            # If file is not m4a, still consider it successful but skip metadata
            if not output_filename.lower().endswith('.m4a'):
                ext = os.path.splitext(output_filename)[1]
                print(f"✅ Successfully downloaded as {ext} format (metadata requires M4A)")
                return True

            audio = MP4(output_filename)
            for key in list(audio.keys()):
                if key.startswith('\xa9') or key in ['covr']:
                    try:
                        del audio[key]
                    except Exception:
                        pass
            audio['\xa9nam'] = [original_base]
            audio['\xa9ART'] = [artist]
            audio['\xa9alb'] = [album_title]
            audio['\xa9gen'] = [genre]
            if track_num:
                audio['trkn'] = [(track_num, total_tracks or 0)]
            if 'upload_date' in entry:
                audio['©day'] = [str(entry.get('upload_date', ''))[:4]]
            if cover_art_path and os.path.exists(cover_art_path):
                with open(cover_art_path, "rb") as f:
                    cover_data = f.read()
                try:
                    audio['covr'] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]
                except Exception:
                    pass
            audio.save()
            folder_art_path = os.path.splitext(output_filename)[0] + ".jpg"
            if cover_art_path and os.path.exists(cover_art_path):
                try:
                    shutil.copy2(cover_art_path, folder_art_path)
                except Exception:
                    pass
            return True
        except Exception:
            return False
    except Exception:
        return False
def check_available_formats(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if '_type' in info and info['_type'] == 'playlist':
                entries = [entry for entry in info.get('entries', []) if entry]
                if entries:
                    formats = entries[0].get('formats', [])
                    title = entries[0].get('title', 'Unknown')
                else:
                    return []
            else:
                formats = info.get('formats', [])
                title = info.get('title', 'Unknown')
            audio_formats = [f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
            return audio_formats
    except Exception:
        return []

def main():
    # Simple wrapper to allow running engine directly if needed
    try:
        url = input("Enter the YouTube URL: ")
        if url:
            print("Use the GUI or import engine functions from the TrackOut package.")
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
