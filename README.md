# YouTube Music Extractor

A Python tool to download music from YouTube/YouTube Music with proper metadata and album art.

## Features

- Download music from YouTube or YouTube Music URLs
- Convert to high-quality M4A format
- Extract and embed metadata (title, artist, album, etc.)
- Process album artwork to a perfect 1:1 aspect ratio
- Optimize cover art for media players

## Requirements

- Python 3.7+
- Dependencies listed in `requirements.txt`

## Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/YTMusic_To_M4A.git
cd YTMusic_To_M4A
```

2. Create and activate a virtual environment (optional but recommended)
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

## Usage

Run the script and provide a YouTube/YouTube Music URL:

```bash
python main.py
```

The script will:
1. Download the best audio quality
2. Convert to M4A format
3. Extract metadata from YouTube
4. Download, crop and optimize the cover art
5. Embed metadata and cover art
6. Clean up temporary files

## Examples

```bash
# After running the script:
Enter the YouTube URL: https://music.youtube.com/watch?v=15tpdUBflC0
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube download functionality
- [MoviePy](https://github.com/Zulko/moviepy) for audio conversion
- [Mutagen](https://github.com/quodlibet/mutagen) for metadata handling
- [Pillow](https://github.com/python-pillow/Pillow) for image processing
