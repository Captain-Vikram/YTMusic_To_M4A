#!/usr/bin/env python3
"""
YouTube Music Extractor - Streamlit Web App (Fixed Version)
A modern web interface for downloading YouTube music with metadata and cover art.

Features:
- Clean and intuitive web interface
- Real-time progress tracking
- Quality selection options
- Download history
- Mobile-friendly design
- Better error handling for web deployment
"""

import streamlit as st
import os
import sys
import tempfile
from pathlib import Path
import zipfile
from datetime import datetime

# Add current directory to path to import main functions
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    import yt_dlp
    # Import existing functions from main.py
    from main import (
        sanitize_filename,
        process_cover_art,
        process_single_track
    )
except ImportError as e:
    st.error(f"Import Error: {e}")
    st.error("Please ensure all required packages are installed and main.py is in the same directory.")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="🎵 YouTube Music Extractor",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    
    .info-message {
        background: #d1ecf1;
        color: #0c5460;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #17a2b8;
    }
    
    .stProgress > div > div > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'download_history' not in st.session_state:
    st.session_state.download_history = []

def is_valid_youtube_url(url):
    """Check if URL is a valid YouTube URL"""
    if not url:
        return False
    youtube_domains = ['youtube.com', 'youtu.be', 'music.youtube.com']
    return any(domain in url for domain in youtube_domains)

def extract_video_info(url):
    """Extract video information without downloading"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        st.error(f"Error extracting video info: {str(e)}")
        return None

def download_youtube_content(url, output_dir, quality_format, progress_callback=None):
    """Download YouTube content using existing functions"""
    original_cwd = os.getcwd()
    
    try:
        # For web deployment, always use temp directory
        output_dir = tempfile.mkdtemp(prefix="youtube_download_")
        
        # Change to output directory
        os.chdir(output_dir)
        
        # Progress hook for yt-dlp
        def progress_hook(d):
            try:
                if progress_callback and d.get('status') == 'downloading':
                    if '_percent_str' in d:
                        try:
                            percent = float(d['_percent_str'].replace('%', ''))
                            progress = int(percent * 0.7)  # 70% for download
                            progress_callback(progress, f"Downloading: {d['_percent_str']}")
                        except (ValueError, TypeError):
                            progress_callback(10, "Downloading...")
            except Exception:
                pass
        
        # Extract info first
        ydl_opts_info = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return False, "Could not extract video information", None
        
        # Determine if it's a playlist or single video
        is_playlist = 'entries' in info and info.get('entries') and len(info.get('entries', [])) > 1
        
        if is_playlist:
            album_title = sanitize_filename(info.get('title', 'Unknown Album'))
            album_folder = album_title
            entries = [entry for entry in info.get('entries', []) if entry is not None]
            
            if progress_callback:
                progress_callback(5, f"Found {len(entries)} tracks in album: {album_title}")
        else:
            album_title = sanitize_filename(info.get('title', 'Unknown'))
            album_folder = f"Single - {album_title}"
            entries = [info]
            
            if progress_callback:
                progress_callback(5, f"Processing single track: {album_title}")
        
        # Create album folder
        if not os.path.exists(album_folder):
            os.makedirs(album_folder, exist_ok=True)
        
        # Download options with better error handling
        ydl_opts = {
            'format': quality_format,
            'writeinfojson': False,
            'writethumbnail': True,
            'outtmpl': '%(title)s.%(ext)s',
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'extractaudio': True,
            'audioformat': 'm4a',
            'audioquality': '256K',
            'socket_timeout': 30,
            'retries': 3
        }
        
        # Download content
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if progress_callback:
            progress_callback(70, "Processing downloaded files...")
        
        # Process each track with better error handling
        success_count = 0
        for i, entry in enumerate(entries, 1):
            if entry is None:
                continue
                
            try:
                if progress_callback:
                    progress_callback(70 + (20 * i // len(entries)), f"Processing track {i}/{len(entries)}")
                
                success = process_single_track(
                    entry, 
                    album_folder, 
                    None,  # Cover art will be found automatically
                    album_title, 
                    i if is_playlist else None, 
                    len(entries) if is_playlist else None
                )
                if success:
                    success_count += 1
                    
            except Exception as e:
                if progress_callback:
                    progress_callback(70 + (20 * i // len(entries)), f"Error processing track {i}: {str(e)}")
                continue
        
        # Cleanup temporary files
        if progress_callback:
            progress_callback(95, "Cleaning up temporary files...")
        
        try:
            # Clean up downloaded files that aren't M4A
            for file in os.listdir('.'):
                if (file.endswith(('.webm', '.mp4', '.opus', '.webp', '.jpg', '.png', '.info.json')) 
                    and not file.startswith(album_folder)):
                    try:
                        os.remove(file)
                    except (OSError, PermissionError):
                        pass
        except Exception:
            pass
        
        if progress_callback:
            progress_callback(100, f"Completed! Downloaded {success_count} tracks")
        
        # Return to original directory
        os.chdir(original_cwd)
        
        return True, f"Successfully downloaded {success_count} tracks", os.path.join(output_dir, album_folder)
        
    except Exception as e:
        # Make sure we return to original directory
        try:
            os.chdir(original_cwd)
        except:
            pass
        return False, f"Download failed: {str(e)}", None

def create_download_archive(folder_path):
    """Create a ZIP archive of the downloaded music folder"""
    try:
        zip_path = f"{folder_path}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(folder_path))
                    zipf.write(file_path, arcname)
        return zip_path
    except Exception as e:
        st.error(f"Error creating archive: {str(e)}")
        return None

# Main app interface
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎵 YouTube Music Extractor</h1>
        <p>Download high-quality music with metadata and cover art</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Quality selection
        quality_options = {
            "Best Quality (Recommended)": "bestaudio[ext=m4a]/bestaudio/best",
            "High Quality (256k)": "bestaudio[abr<=256]/best",
            "Medium Quality (128k)": "bestaudio[abr<=128]/best",
            "Any Quality": "bestaudio/best"
        }
        
        selected_quality = st.selectbox(
            "🎧 Audio Quality",
            options=list(quality_options.keys()),
            index=0
        )
        
        # Download history
        st.header("📋 Recent Downloads")
        if st.session_state.download_history:
            for i, download in enumerate(reversed(st.session_state.download_history[-5:])):
                with st.expander(f"📁 {download['title'][:30]}..."):
                    st.write(f"**URL:** {download['url']}")
                    st.write(f"**Date:** {download['date']}")
                    st.write(f"**Status:** {download['status']}")
        else:
            st.info("No downloads yet")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🎯 Download Music")
        
        # URL input
        url_input = st.text_input(
            "🔗 YouTube/YouTube Music URL",
            placeholder="https://music.youtube.com/watch?v=... or https://youtube.com/playlist?list=...",
            help="Paste a YouTube or YouTube Music URL here"
        )
        
        # URL validation
        if url_input:
            if is_valid_youtube_url(url_input):
                st.success("✅ Valid YouTube URL")
                
                # Show video info if available
                if st.button("🔍 Preview Content"):
                    with st.spinner("Analyzing URL..."):
                        info = extract_video_info(url_input)
                        if info:
                            if 'entries' in info and info.get('entries') and len(info.get('entries', [])) > 1:
                                st.info(f"📀 **Album/Playlist:** {info.get('title', 'Unknown')}")
                                st.write(f"**Tracks:** {len(info['entries'])}")
                            else:
                                st.info(f"🎵 **Single Track:** {info.get('title', 'Unknown')}")
                                st.write(f"**Uploader:** {info.get('uploader', 'Unknown')}")
                
            else:
                st.error("❌ Please enter a valid YouTube URL")
        
        # Download section
        st.header("⬇️ Download")
        
        download_button = st.button(
            "🚀 Start Download",
            disabled=not url_input or not is_valid_youtube_url(url_input),
            use_container_width=True
        )
        
        # Handle download
        if download_button and url_input and is_valid_youtube_url(url_input):
            # Progress display containers
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Progress callback that updates the UI immediately
            def update_progress(progress, status):
                progress_bar.progress(progress / 100)
                status_text.text(status)
            
            # Run download
            try:
                with st.spinner("Downloading..."):
                    success, message, folder_path = download_youtube_content(
                        url_input,
                        None,  # Will use temp directory
                        quality_options[selected_quality],
                        update_progress
                    )
                
                if success:
                    st.success(f"✅ {message}")
                    
                    # Add to download history
                    download_record = {
                        'url': url_input,
                        'title': message.split(' to ')[-1] if ' to ' in message else 'Unknown',
                        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'status': 'Success',
                        'folder_path': folder_path
                    }
                    st.session_state.download_history.append(download_record)
                    
                    # Option to create downloadable archive
                    if folder_path and os.path.exists(folder_path):
                        if st.button("📦 Create Downloadable Archive"):
                            with st.spinner("Creating archive..."):
                                archive_path = create_download_archive(folder_path)
                                if archive_path and os.path.exists(archive_path):
                                    with open(archive_path, 'rb') as f:
                                        st.download_button(
                                            label="💾 Download ZIP Archive",
                                            data=f.read(),
                                            file_name=os.path.basename(archive_path),
                                            mime="application/zip"
                                        )
                        
                else:
                    st.error(f"❌ {message}")
                    
                    # Add to download history
                    download_record = {
                        'url': url_input,
                        'title': 'Failed Download',
                        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'status': f'Failed: {message}',
                        'folder_path': None
                    }
                    st.session_state.download_history.append(download_record)
            
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
                st.error("This might be due to regional restrictions, private videos, or network issues.")
    
    with col2:
        st.header("ℹ️ Information")
        
        # Feature highlights
        st.markdown("""
        <div class="info-message">
        <h4>✨ Features</h4>
        <ul>
        <li>🎵 High-quality audio extraction</li>
        <li>🖼️ Automatic metadata and cover art</li>
        <li>📁 Smart file organization</li>
        <li>⚡ Fast processing</li>
        <li>🎧 Multiple quality options</li>
        <li>📱 Mobile-friendly interface</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Supported formats
        with st.expander("📋 Supported Formats"):
            st.write("""
            **Input:**
            - YouTube Music URLs
            - YouTube video URLs
            - YouTube playlist URLs
            - YouTube album URLs
            
            **Output:**
            - M4A format with AAC codec
            - Embedded metadata
            - Cover art (embedded + external)
            - Organized folder structure
            """)
        
        # Tips
        with st.expander("💡 Tips"):
            st.write("""
            - Use YouTube Music URLs for best metadata
            - Albums/playlists are processed automatically
            - Files are organized in folders
            - Cover art is optimized for media players
            - Download the ZIP archive to get your files
            """)

if __name__ == "__main__":
    main()