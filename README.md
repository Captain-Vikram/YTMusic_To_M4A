# YouTube Music Extractor

A Python tool to download music from YouTube/YouTube Music with proper metadata and album art, featuring parallel processing for albums and playlists.

## Features

- 🎵 Download music from YouTube or YouTube Music URLs
- 📀 Support for both single tracks and full albums/playlists
- 🚀 **Parallel processing** for faster album downloads
- 🎧 Convert to high-quality M4A format with 256k bitrate
- 🏷️ Extract and embed metadata (title, artist, album, genre, track numbers)
- 🖼️ Process album artwork to perfect 1:1 aspect ratio (500x500px)
- 📁 Organized folder structure for albums and single tracks
- 🧹 Automatic cleanup of temporary files
- 🎮 Optimize for VLC and other media players

## Requirements

- Python 3.7+
- Dependencies listed in `requirements.txt`

## Installation

### Option 1: Clone and Install
```bash
git clone https://github.com/Captain-Vikram/YTMusic_To_M4A
cd YTMusic_To_M4A
```

### Option 2: Install as Package
```bash
pip install -e .
```

### Set up Virtual Environment (Recommended)
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage
```bash
python main.py
```

### As Installed Package
```bash
yt-music-extractor
```

The script will prompt you for a YouTube/YouTube Music URL and then:

1. **Analyze** the URL to determine if it's a single track or album/playlist
2. **Download** the best audio quality using yt-dlp
3. **Convert** to M4A format with AAC codec (256k bitrate)
4. **Process** cover art (crop to square, resize to 500x500px)
5. **Embed** metadata and cover art into audio files
6. **Organize** files into appropriate folders
7. **Clean up** temporary files

## Examples

### Single Track
```bash
Enter the YouTube URL: https://music.youtube.com/watch?v=dQw4w9WgXcQ
```
Creates: `Single - Song Title/Song Title.m4a`

### Album/Playlist
```bash
Enter the YouTube URL: https://music.youtube.com/playlist?list=OLAK5uy_xyz
```
Creates: `Album Title/Track 1.m4a`, `Album Title/Track 2.m4a`, etc.

## Features in Detail

### Parallel Processing
- Albums and playlists are processed using ThreadPoolExecutor
- Up to 4 concurrent downloads (configurable in `config.py`)
- Real-time progress tracking

### Metadata Handling
- **Title**: Song title from YouTube
- **Artist**: Channel name or extracted artist
- **Album**: Playlist/album title or song title for singles
- **Genre**: "YouTube Music" (default)
- **Track Numbers**: Automatic numbering for album tracks
- **Cover Art**: Embedded as MP4Cover format

### File Organization
```
Project Root/
├── Album Title/
│   ├── Track 1.m4a
│   ├── Track 2.m4a
│   ├── cover.jpg
│   └── Track 1.jpg (external cover for VLC)
└── Single - Song Title/
    ├── Song Title.m4a
    └── cover.jpg
```

### Image Processing
- Automatically crops images to 1:1 aspect ratio
- Resizes to 500x500px for optimal compatibility
- Converts to JPEG format (95% quality)
- Creates both embedded and external cover art

## Configuration

Modify settings in [`config.py`](config.py):

```python
# Audio quality
AUDIO_BITRATE = "256k"

# Image processing
IMAGE_TARGET_SIZE = 500
IMAGE_QUALITY = 95

# Threading
MAX_WORKERS = 4
```

## Troubleshooting

### Common Issues

1. **Missing audio files**: Check if the URL is accessible and not geo-blocked
2. **Conversion errors**: Ensure FFmpeg is installed and accessible
3. **Metadata errors**: Some files may not support M4A metadata format

### Debug Mode
Add verbose logging by modifying the yt-dlp options in the script.

## Dependencies

- **yt-dlp**: YouTube download functionality
- **moviepy**: Audio conversion and processing
- **mutagen**: Audio metadata handling
- **Pillow**: Image processing and manipulation
- **requests**: HTTP requests for thumbnail downloads

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for robust YouTube download functionality
- [MoviePy](https://github.com/Zulko/moviepy) for audio conversion capabilities
- [Mutagen](https://github.com/quodlibet/mutagen) for comprehensive metadata handling
- [Pillow](https://github.com/python-pillow/Pillow) for advanced image processing

## Changelog

### v1.0.2 (Latest)
- 🐛 Fixed bug in metadata handling
- 📖 Updated documentation

### v1.0.1
- 🚀 Initial PyPI release
- 📦 Fixed packaging issues
- All features from v1.0.0 included

### v1.0.0
- 🚀 Added parallel processing for albums and playlists
- 📁 Improved file organization with dedicated folders
- 🖼️ Enhanced image processing with 1:1 aspect ratio cropping
- 🧹 Automatic cleanup of temporary files
- 📊 Better error handling and progress tracking
- 🎮 VLC-optimized output with external cover art files