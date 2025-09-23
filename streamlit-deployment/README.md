# 🎵 YouTube Music Extractor - Streamlit Web App

A web-based application built with Streamlit for downloading and extracting metadata from YouTube music videos. This is the web deployment version of the YouTube Music Extractor project.

## 🌐 Live Demo

[**Try the app here**](https://your-streamlit-app.streamlit.app) *(Replace with your actual Streamlit Cloud URL)*

## ✨ Features

- **🎵 High-Quality Audio Download**: Download music in M4A format with 256k bitrate
- **🖼️ Automatic Metadata Extraction**: Album art, title, artist, and more
- **📱 Web-Based Interface**: Access from any device with a browser
- **⚡ Real-Time Progress**: Live download progress tracking
- **🎯 Multiple Quality Options**: Choose from various audio quality settings
- **📂 Easy Organization**: Automatic file naming and organization

## 🚀 Quick Start

### Option 1: Use the Live App
Simply visit the [live app](https://your-streamlit-app.streamlit.app) and start downloading!

### Option 2: Run Locally
```bash
# Clone the repository
git clone https://github.com/Captain-Vikram/YTMusic_To_M4A.git
cd YTMusic_To_M4A

# Switch to streamlit branch
git checkout streamlit-deployment

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run streamlit_app.py
```

## 💻 Usage

1. **Enter YouTube URL**: Paste any YouTube music video URL
2. **Select Quality**: Choose your preferred audio quality
3. **Choose Output Directory**: Select where to save the file
4. **Download**: Click download and watch the progress
5. **Enjoy**: Your high-quality M4A file is ready!

## 🛠️ Technology Stack

- **Frontend**: Streamlit
- **Backend**: Python
- **Download Engine**: yt-dlp
- **Audio Processing**: MoviePy
- **Metadata**: Mutagen
- **Image Processing**: Pillow

## 📋 Requirements

- Python 3.10+
- Internet connection
- Modern web browser

## 🔧 Development

### Local Development Setup
```bash
# Clone and setup
git clone https://github.com/Captain-Vikram/YTMusic_To_M4A.git
cd YTMusic_To_M4A
git checkout streamlit-deployment

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run in development mode
streamlit run streamlit_app.py --server.runOnSave true
```

### Project Structure
```
streamlit-deployment/
├── streamlit_app.py          # Main Streamlit application
├── main.py                   # Core download functionality
├── config.py                 # Configuration settings
├── requirements.txt          # Python dependencies
├── runtime.txt              # Python version for deployment
└── README.md                # This file
```

## 🌍 Deployment

### Streamlit Cloud Deployment
1. Fork this repository
2. Connect your GitHub account to [Streamlit Cloud](https://streamlit.io/cloud)
3. Select the `streamlit-deployment` branch
4. Set the main file as `streamlit_app.py`
5. Deploy!

### Other Deployment Options
- **Heroku**: Use the included `runtime.txt` and `requirements.txt`
- **Railway**: Direct deployment from GitHub
- **Render**: Web service deployment
- **Docker**: Containerized deployment

## 🔒 Environment Variables

For production deployment, set these environment variables:
- `YOUTUBE_API_KEY`: (Optional) For enhanced functionality
- `DEFAULT_OUTPUT_DIR`: Default download directory

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube downloading capabilities
- [Streamlit](https://streamlit.io/) for the amazing web framework
- [MoviePy](https://zulko.github.io/moviepy/) for audio processing

## 📞 Support

If you encounter any issues or have questions:
- Open an issue on GitHub
- Check the [FAQ section](https://github.com/Captain-Vikram/YTMusic_To_M4A/wiki/FAQ)
- Contact the maintainer

---

**⭐ If you find this project useful, please give it a star!** ⭐