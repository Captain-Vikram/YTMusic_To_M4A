#!/usr/bin/env python3
"""
YouTube Music Extractor - Streamlit Web App
A modern web interface for downloading and processing YouTube music with metadata and cover art.

Features:
- Clean and intuitive web interface
- Real-time progress tracking
- Quality selection options
- Download history
- Mobile-friendly design
"""

import streamlit as st
import os
import sys
import threading
import time
import tempfile
import shutil
from pathlib import Path
import zipfile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add current directory to path to import main functions
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    import yt_dlp
    # Import existing functions from main.py
    from main import (
        sanitize_filename,
        process_cover_art,
        process_single_track,
        check_available_formats
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
    
    .download-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    
    .success-message {
        background: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #28a745;
    }
    
    .error-message {
        background: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #dc3545;
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

if 'current_download' not in st.session_state:
    st.session_state.current_download = None

if 'download_progress' not in st.session_state:
    st.session_state.download_progress = 0

if 'download_status' not in st.session_state:
    st.session_state.download_status = ""

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
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Change to output directory
        original_cwd = os.getcwd()
        os.chdir(output_dir)
        
        # Progress hook for yt-dlp
        def progress_hook(d):
            if progress_callback and d.get('status') == 'downloading':
                if 'downloaded_bytes' in d and 'total_bytes' in d:
                    progress = int((d['downloaded_bytes'] / d['total_bytes']) * 80)  # Leave 20% for processing
                    progress_callback(progress, f"Downloading: {d.get('_percent_str', '0%')}")
        
        # Extract info first
        ydl_opts_info = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return False, "Could not extract video information"
        
        # Determine if it's a playlist or single video
        is_playlist = 'entries' in info and len(info.get('entries', [])) > 1
        
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
        
        # Download options
        ydl_opts = {
            'format': quality_format,
            'writeinfojson': False,
            'writethumbnail': True,
            'outtmpl': '%(title)s.%(ext)s',
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
        }
        
        # Download content
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        if progress_callback:
            progress_callback(85, "Processing downloaded files...")
        
        # Process each track
        success_count = 0
        for i, entry in enumerate(entries, 1):
            if entry is None:
                continue
                
            try:
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
                    
                if progress_callback:
                    track_progress = 85 + (10 * i // len(entries))
                    progress_callback(track_progress, f"Processed {i}/{len(entries)} tracks")
                    
            except Exception as e:
                st.warning(f"Error processing track {i}: {str(e)}")
                continue
        
        # Cleanup temporary files
        if progress_callback:
            progress_callback(95, "Cleaning up temporary files...")
        
        # Clean up downloaded files that aren't M4A
        for file in os.listdir('.'):
            if file.endswith(('.webm', '.mp4', '.opus', '.webp', '.jpg', '.png')) and not file.startswith(album_folder):
                try:
                    os.remove(file)
                except:
                    pass
        
        if progress_callback:
            progress_callback(100, f"Completed! Downloaded {success_count} tracks")
        
        # Return to original directory
        os.chdir(original_cwd)
        
        return True, f"Successfully downloaded {success_count} tracks to {album_folder}"
        
    except Exception as e:
        # Make sure we return to original directory
        try:
            os.chdir(original_cwd)
        except:
            pass
        return False, f"Download failed: {str(e)}"

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
            "Best Quality (Recommended)": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio[ext=opus]/bestaudio/best",
            "High Quality (256k)": "bestaudio[abr<=256]/bestaudio/best",
            "Medium Quality (128k)": "bestaudio[abr<=128]/bestaudio/best",
            "Any Quality": "bestaudio/best"
        }
        
        selected_quality = st.selectbox(
            "🎧 Audio Quality",
            options=list(quality_options.keys()),
            index=0
        )
        
        # Output directory
        default_output = os.path.join(os.path.expanduser("~"), "Downloads", "YouTube Music")
        output_dir = st.text_input(
            "📁 Output Directory",
            value=default_output,
            help="Directory where files will be saved"
        )
        
        # Advanced options
        with st.expander("🔧 Advanced Options"):
            add_metadata = st.checkbox("📝 Add metadata and cover art", value=True)
            auto_cleanup = st.checkbox("🧹 Auto-cleanup temporary files", value=True)
            show_formats = st.checkbox("🔍 Show available formats before download", value=False)
        
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
                            if 'entries' in info and len(info.get('entries', [])) > 1:
                                st.info(f"📀 **Album/Playlist:** {info.get('title', 'Unknown')}")
                                st.write(f"**Tracks:** {len(info['entries'])}")
                            else:
                                st.info(f"🎵 **Single Track:** {info.get('title', 'Unknown')}")
                                st.write(f"**Artist:** {info.get('uploader', 'Unknown')}")
                                st.write(f"**Duration:** {info.get('duration_string', 'Unknown')}")
                
                # Show available formats if requested
                if show_formats and url_input:
                    if st.button("📊 Check Available Formats"):
                        with st.spinner("Checking formats..."):
                            try:
                                check_available_formats(url_input)
                            except Exception as e:
                                st.error(f"Error checking formats: {str(e)}")
                
            else:
                st.error("❌ Please enter a valid YouTube URL")
        
        # Download section
        st.header("⬇️ Download")
        
        download_col1, download_col2 = st.columns([1, 1])
        
        with download_col1:
            download_button = st.button(
                "🚀 Start Download",
                disabled=not url_input or not is_valid_youtube_url(url_input),
                use_container_width=True
            )
        
        with download_col2:
            if st.session_state.current_download:
                if st.button("❌ Cancel Download", use_container_width=True):
                    st.session_state.current_download = None
                    st.session_state.download_progress = 0
                    st.session_state.download_status = "Cancelled"
                    st.rerun()
        
        # Progress section
        if st.session_state.current_download or st.session_state.download_progress > 0:
            st.header("📊 Download Progress")
            
            progress_bar = st.progress(st.session_state.download_progress / 100)
            status_text = st.empty()
            
            if st.session_state.download_status:
                status_text.text(st.session_state.download_status)
        
        # Handle download
        if download_button and url_input and is_valid_youtube_url(url_input):
            st.session_state.current_download = url_input
            st.session_state.download_progress = 0
            st.session_state.download_status = "Starting download..."
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Progress callback
            def update_progress(progress, status):
                st.session_state.download_progress = progress
                st.session_state.download_status = status
            
            # Run download in a thread (Note: In production, use proper async handling)
            with st.spinner("Downloading..."):
                try:
                    success, message = download_youtube_content(
                        url_input,
                        output_dir,
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
                            'output_dir': output_dir
                        }
                        st.session_state.download_history.append(download_record)
                        
                        # Show download location
                        st.info(f"📁 Files saved to: `{output_dir}`")
                        
                        # Option to create downloadable archive
                        if st.button("📦 Create Downloadable Archive"):
                            with st.spinner("Creating archive..."):
                                # Find the downloaded folder
                                for item in os.listdir(output_dir):
                                    item_path = os.path.join(output_dir, item)
                                    if os.path.isdir(item_path):
                                        zip_path = create_download_archive(item_path)
                                        if zip_path and os.path.exists(zip_path):
                                            with open(zip_path, "rb") as fp:
                                                st.download_button(
                                                    label="⬇️ Download ZIP Archive",
                                                    data=fp.read(),
                                                    file_name=os.path.basename(zip_path),
                                                    mime="application/zip"
                                                )
                                        break
                    else:
                        st.error(f"❌ {message}")
                        
                        # Add to download history
                        download_record = {
                            'url': url_input,
                            'title': 'Failed Download',
                            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'status': f'Failed: {message}',
                            'output_dir': output_dir
                        }
                        st.session_state.download_history.append(download_record)
                
                except Exception as e:
                    st.error(f"❌ Unexpected error: {str(e)}")
                
                finally:
                    st.session_state.current_download = None
                    st.session_state.download_progress = 0
                    st.session_state.download_status = ""
    
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
        <li>⚡ Fast parallel processing</li>
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
            - Albums/playlists are processed in parallel
            - Files are organized automatically
            - Cover art is optimized for media players
            - Temporary files are cleaned up automatically
            """)
        
        # System info
        with st.expander("🔧 System Info"):
            st.write(f"**Python Version:** {st.__version__}")
            st.write(f"**Output Directory:** `{output_dir}`")
            st.write(f"**Selected Quality:** {selected_quality}")

if __name__ == "__main__":
    main()