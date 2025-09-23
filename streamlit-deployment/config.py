"""
Configuration settings for the YouTube Music Extractor.
"""

# Default output format
DEFAULT_FORMAT = "m4a"

# Audio quality settings
AUDIO_BITRATE = "256k"

# Image processing settings
IMAGE_TARGET_SIZE = 500  # Target size for cover art (pixels)
IMAGE_QUALITY = 95  # JPEG quality (1-100)

# Threading settings
MAX_WORKERS = 4  # Maximum number of concurrent downloads

# Download options for yt-dlp
DOWNLOAD_OPTIONS = {
    'format': 'bestaudio/best',
    'writeinfojson': False,  # Don't need JSON files
    'writethumbnail': True,
    'outtmpl': '%(title)s.%(ext)s'
}

# Info extraction options
INFO_EXTRACTION_OPTIONS = {
    'quiet': True,
    'no_warnings': True,
}

# File extensions to process
AUDIO_EXTENSIONS = ['webm', 'mp4', 'm4a', 'opus']
IMAGE_EXTENSIONS = ['jpg', 'webp', 'png', 'jpeg']

# Cleanup settings
PROJECT_EXTENSIONS = {'.py', '.md', '.txt', '.json', '.gitignore'}
IMPORTANT_FILES = {'LICENSE', 'setup.py', 'requirements.txt'}
TEMP_FILES = ['temp_cover.jpg']