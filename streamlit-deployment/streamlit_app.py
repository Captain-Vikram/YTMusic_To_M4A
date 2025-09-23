#!/usr/bin/env python3
"""
YouTube Music Extractor - Streamlit Web App (Cloud-Ready Version)
A modern web interface for downloading YouTube music with automatic ZIP delivery.

Key Features for Cloud Deployment:
- Automatic ZIP file creation and download
- In-memory file processing
- Session state management for cloud environments
- Optimized for platforms like Streamlit Cloud, Heroku, etc.
"""

import streamlit as st
import os
import sys
import tempfile
from pathlib import Path
import zipfile
from datetime import datetime
import io
import shutil
import atexit

# Add current directory to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    import yt_dlp
    from main import sanitize_filename
except ImportError as e:
    st.error(f"Import Error: {e}")
    st.error("Please ensure all required packages are installed.")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="🎵 YouTube Music Extractor",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1.5rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .download-section {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    
    .info-box {
        background: #e3f2fd;
        color: #1565c0;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
    
    .stProgress > div > div > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'downloads' not in st.session_state:
    st.session_state.downloads = {}
if 'download_counter' not in st.session_state:
    st.session_state.download_counter = 0

def cleanup_temp_dirs():
    """Clean up temporary directories on app exit"""
    try:
        temp_base = tempfile.gettempdir()
        for item in os.listdir(temp_base):
            if item.startswith('youtube_download_'):
                item_path = os.path.join(temp_base, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path, ignore_errors=True)
    except:
        pass

# Register cleanup function
atexit.register(cleanup_temp_dirs)

def is_valid_youtube_url(url):
    """Check if URL is a valid YouTube URL"""
    if not url:
        return False
    youtube_domains = ['youtube.com', 'youtu.be', 'music.youtube.com']
    return any(domain in url for domain in youtube_domains)

def get_video_info(url):
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
        return None

def download_and_convert(url, quality_format):
    """Download YouTube content and return ZIP file data"""
    temp_dir = None
    
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix="youtube_download_")
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        
        # Get video info
        info = get_video_info(url)
        if not info:
            return None, "Could not extract video information"
        
        # Determine content type
        is_playlist = 'entries' in info and len(info.get('entries', [])) > 1
        
        if is_playlist:
            title = sanitize_filename(info.get('title', 'Unknown Album'))
            entries = [e for e in info.get('entries', []) if e is not None]
        else:
            title = sanitize_filename(info.get('title', 'Unknown Track'))
            entries = [info]
        
        # Create output folder
        output_folder = title
        os.makedirs(output_folder, exist_ok=True)
        
        # Download options optimized for cloud
        ydl_opts = {
            'format': quality_format,
            'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
            'writeinfojson': False,
            'writethumbnail': True,
            'extractaudio': True,
            'audioformat': 'm4a',
            'audioquality': '256K',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'socket_timeout': 30,
            'retries': 3,
            'fragment_retries': 3,
        }
        
        # Download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Verify download
        if not os.path.exists(output_folder) or not os.listdir(output_folder):
            return None, "Download failed - no files created"
        
        # Clean up non-audio files
        for file in os.listdir(output_folder):
            if not file.endswith(('.m4a', '.mp3', '.aac')):
                try:
                    os.remove(os.path.join(output_folder, file))
                except:
                    pass
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(output_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join(title, file)
                    zipf.write(file_path, arcname)
        
        # Count successful files
        audio_files = [f for f in os.listdir(output_folder) if f.endswith(('.m4a', '.mp3', '.aac'))]
        
        # Return to original directory and cleanup
        os.chdir(original_cwd)
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue(), f"Successfully processed {len(audio_files)} files"
        
    except Exception as e:
        # Cleanup on error
        try:
            if temp_dir and os.path.exists(temp_dir):
                os.chdir(original_cwd)
                shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
        return None, f"Error: {str(e)}"

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎵 YouTube Music Extractor</h1>
        <p>Download high-quality music with automatic ZIP delivery</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        quality_options = {
            "Best Quality": "bestaudio[ext=m4a]/bestaudio/best",
            "High Quality (256k)": "bestaudio[abr<=256]/best", 
            "Medium Quality (128k)": "bestaudio[abr<=128]/best",
            "Any Quality": "bestaudio/best"
        }
        
        selected_quality = st.selectbox(
            "🎧 Audio Quality",
            options=list(quality_options.keys()),
            index=0
        )
        
        st.markdown("---")
        st.header("📊 Download Stats")
        st.metric("Total Downloads", len(st.session_state.downloads))
        
        if st.session_state.downloads:
            st.header("📥 Recent Downloads")
            recent = list(st.session_state.downloads.items())[-3:]
            for download_id, download_data in reversed(recent):
                with st.expander(f"🎵 {download_data['title'][:25]}..."):
                    st.write(f"**Date:** {download_data['timestamp']}")
                    if download_data.get('zip_data'):
                        st.download_button(
                            "📥 Re-download",
                            data=download_data['zip_data'],
                            file_name=download_data['filename'],
                            mime="application/zip",
                            key=f"redownload_{download_id}"
                        )
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🎯 Download Music")
        
        # URL Input
        url = st.text_input(
            "🔗 YouTube/YouTube Music URL",
            placeholder="https://music.youtube.com/watch?v=... or https://youtube.com/playlist?list=...",
            help="Paste any YouTube or YouTube Music URL"
        )
        
        # URL validation and preview
        if url:
            if is_valid_youtube_url(url):
                st.success("✅ Valid YouTube URL")
                
                # Preview button
                if st.button("🔍 Preview Content", key="preview_btn"):
                    with st.spinner("Analyzing content..."):
                        info = get_video_info(url)
                        if info:
                            if 'entries' in info and len(info.get('entries', [])) > 1:
                                st.info(f"📀 **Playlist/Album:** {info.get('title', 'Unknown')}")
                                st.write(f"**Tracks:** {len(info['entries'])}")
                            else:
                                st.info(f"🎵 **Single Track:** {info.get('title', 'Unknown')}")
                                st.write(f"**Channel:** {info.get('uploader', 'Unknown')}")
                        else:
                            st.error("Could not analyze this URL")
            else:
                st.error("❌ Please enter a valid YouTube URL")
        
        # Download section
        st.markdown("---")
        
        download_btn = st.button(
            "🚀 Download Music",
            disabled=not url or not is_valid_youtube_url(url),
            use_container_width=True,
            key="main_download_btn"
        )
        
        # Handle download
        if download_btn and url:
            # Generate unique download ID
            st.session_state.download_counter += 1
            download_id = f"download_{st.session_state.download_counter}_{datetime.now().strftime('%H%M%S')}"
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Status updates
            status_text.text("🔍 Analyzing URL...")
            progress_bar.progress(10)
            
            status_text.text("⬇️ Downloading content...")
            progress_bar.progress(30)
            
            # Perform download
            try:
                zip_data, message = download_and_convert(url, quality_options[selected_quality])
                
                if zip_data:
                    progress_bar.progress(90)
                    status_text.text("📦 Creating ZIP archive...")
                    
                    # Generate filename
                    info = get_video_info(url)
                    if info:
                        if 'entries' in info and len(info.get('entries', [])) > 1:
                            filename = f"{sanitize_filename(info.get('title', 'Unknown_Album'))}.zip"
                        else:
                            filename = f"{sanitize_filename(info.get('title', 'Unknown_Track'))}.zip"
                    else:
                        filename = f"YouTube_Music_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                    
                    # Store in session state
                    st.session_state.downloads[download_id] = {
                        'title': filename.replace('.zip', ''),
                        'zip_data': zip_data,
                        'filename': filename,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'url': url
                    }
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Download completed!")
                    
                    # Success message and download
                    st.markdown("""
                    <div class="download-section">
                        <h3>🎉 Download Completed Successfully!</h3>
                        <p>Your music has been processed and is ready for download as a ZIP file.</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Immediate download button
                    st.download_button(
                        label="📥 Download ZIP File",
                        data=zip_data,
                        file_name=filename,
                        mime="application/zip",
                        key=f"download_btn_{download_id}",
                        use_container_width=True
                    )
                    
                    st.success(f"✅ {message}")
                    st.info("💡 Your download will also be available in the sidebar for re-download.")
                    
                else:
                    st.error(f"❌ Download failed: {message}")
                    
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
                st.error("This may be due to regional restrictions or network issues.")
    
    with col2:
        st.header("ℹ️ Information")
        
        st.markdown("""
        <div class="info-box">
        <h4>✨ Cloud-Ready Features</h4>
        <ul>
        <li>🎵 High-quality M4A audio extraction</li>
        <li>📦 Automatic ZIP file creation</li>
        <li>☁️ Optimized for cloud deployment</li>
        <li>💾 In-memory processing</li>
        <li>🔄 Re-download capability</li>
        <li>📱 Works on all devices</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("📋 Supported Content"):
            st.write("""
            **Input Sources:**
            - YouTube Music tracks & albums
            - YouTube videos & playlists
            - Music channels & compilations
            
            **Output Format:**
            - M4A audio files (256k quality)
            - ZIP archive for easy download
            - Organized folder structure
            """)
        
        with st.expander("💡 Usage Tips"):
            st.write("""
            - YouTube Music URLs provide better metadata
            - Albums/playlists are automatically organized
            - ZIP files contain all tracks in folders
            - Downloads are temporarily stored for re-access
            - Works on Streamlit Cloud, Heroku, and other platforms
            """)
        
        with st.expander("⚠️ Important Notes"):
            st.write("""
            - Respect copyright and terms of service
            - Downloads are for personal use only
            - Some content may be region-restricted
            - File size limits may apply on some platforms
            """)

if __name__ == "__main__":
    main()