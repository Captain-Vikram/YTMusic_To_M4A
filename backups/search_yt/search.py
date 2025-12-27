import yt_dlp
import json
import time
from datetime import datetime
from urllib.parse import quote_plus
from pathlib import Path
from typing import Any, Dict, Optional

def search_youtube_local(query, limit=5):
    """
    Searches YouTube using yt-dlp and returns a structured JSON object.
    """
    
    # 1. Configuration for yt-dlp
    ydl_opts: Dict[str, Any] = {
        'quiet': True,              # Suppress console output
        'extract_flat': True,       # FAST mode: Scrape search page only, don't visit video URLs
        'dump_single_json': True,   # ensure we get structured data back
        'ignoreerrors': True,       # Don't crash on individual video errors
    }

    start_time = time.time()

    # 2. execute search
    results_list = []
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
        try:
            # "ytsearchN:" is the magic prefix to search N results
            search_query = f"ytsearch{limit}:{query}"
            info = ydl.extract_info(search_query, download=False)
            
            if 'entries' in info:
                results_list = list(info['entries'])
        except Exception as e:
            return {"error": str(e)}

    # 3. Calculate timing
    total_time = round(time.time() - start_time, 2)
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    # 4. Transform data into the app's expected JSON structure
    formatted_videos = []
    
    for idx, item in enumerate(results_list):
        if not item: continue

        # Safe extraction of thumbnails (sometimes it's a list, sometimes missing)
        thumb_url = None
        if item.get('thumbnails'):
            # Get the last thumbnail (usually highest quality)
            thumb_url = item['thumbnails'][-1].get('url')
        # Prefer to expose a YouTube Music watch URL for results (music.youtube.com)
        video_id = None
        # yt-dlp often includes 'id' or 'url' fields; try to use 'id' first
        if item.get('id'):
            video_id = item.get('id')
        else:
            u = item.get('url') or item.get('webpage_url') or item.get('original_url')
            if isinstance(u, str) and 'watch?v=' in u:
                # extract v= param
                try:
                    from urllib.parse import urlparse, parse_qs
                    qs = parse_qs(urlparse(u).query)
                    video_id = qs.get('v', [None])[0]
                except Exception:
                    video_id = None

        music_link = None
        if video_id:
            music_link = f"https://music.youtube.com/watch?v={video_id}"

        video_object = {
            "position_on_page": idx + 1,
            "title": item.get('title'),
            # expose music.youtube link when possible, else fall back to available url
            "link": music_link or item.get('url') or item.get('webpage_url'),
            "channel": {
                "name": item.get('uploader'),
                "link": item.get('uploader_url'),
                "verified": False
            },
            "views": item.get('view_count'),
            "description": item.get('description', ''),
            "length": item.get('duration_string'),
            "thumbnail": {
                "static": thumb_url
            }
        }
        formatted_videos.append(video_object)

    # 5. Construct Final JSON Response
    response = {
        "search_metadata": {
            "id": f"local-{int(time.time())}",
            "status": "Success",
            "json_endpoint": "local_function_call",
            "created_at": timestamp,
            "processed_at": timestamp,
            # Use YouTube Music search URL for music-focused queries / UI
            "youtube_url": f"https://music.youtube.com/search?q={quote_plus(query)}",
            "total_time_taken": total_time
        },
        "search_parameters": {
            "engine": "youtube (via yt-dlp)",
            "search_query": query
        },
        # The response contains video results parsed from yt-dlp
        "video_results": formatted_videos
    }

    return response


def download_media(url: str, format_choice: str = "mp3", output_dir: Optional[str] = None):
    """Download a single YouTube URL as mp3 or mp4 using yt-dlp.

    Args:
        url: The YouTube video URL to download.
        format_choice: "mp3" or "mp4".
        output_dir: Optional directory path to save the file.

    Returns:
        dict: {"status": "success"|"error", "filepath": str, "message": str}
    """

    target_dir = Path(output_dir) if output_dir else Path.cwd()
    target_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts: Dict[str, Any] = {
        "outtmpl": str(target_dir / "%(title)s.%(ext)s"),
        "quiet": True,
        "ignoreerrors": True,
        "noplaylist": True,
    }

    if format_choice.lower() == "mp3":
        ydl_opts.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
        )
    else:  # default to mp4
        ydl_opts.update(
            {
                "format": "mp4[height<=1080]/bestvideo+bestaudio/best",
                "merge_output_format": "mp4",
                "postprocessors": [
                    {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}
                ],
            }
        )

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # Postprocessors may change extension; resolve final path
            final_path = next(target_dir.glob(Path(filename).stem + ".*"), Path(filename))
        return {
            "status": "success",
            "filepath": str(final_path),
            "message": "Download completed",
        }
    except Exception as exc:  # pragma: no cover - best effort error capture
        return {"status": "error", "message": str(exc), "filepath": None}

# --- USAGE EXAMPLE ---
if __name__ == "__main__":
    search_term = "star wars"
    
    print(f"Searching for: {search_term}...")
    json_data = search_youtube_local(search_term, limit=3)
    
    # Print as formatted JSON
    print(json.dumps(json_data, indent=2))