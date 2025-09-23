# 🚀 Quick Deployment Guide

This folder contains everything needed to deploy the YouTube Music Extractor as a Streamlit web app.

## 📁 What's Included

```
streamlit-deployment/
├── streamlit_app.py         # Main Streamlit application
├── main.py                  # Core download functionality
├── config.py                # Configuration settings
├── requirements.txt         # Python dependencies
├── runtime.txt             # Python version (3.10.12)
├── .gitignore              # Deployment gitignore
├── README.md               # Full documentation
├── CONTRIBUTING.md         # Contribution guidelines
└── QUICK_START.md          # This file
```

## ⚡ Quick Local Test

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run streamlit_app.py
```

## 🌐 Deploy to Streamlit Cloud

1. **Upload to GitHub:**
   - Create new repository or branch
   - Upload all files from this folder
2. **Deploy on Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub repository
   - Main file: `streamlit_app.py`
   - Click Deploy!

## 🔧 Other Deployment Options

### Railway

```bash
# Just push to GitHub and connect to Railway
# Uses requirements.txt automatically
```

### Heroku

```bash
# Add Procfile:
echo "web: streamlit run streamlit_app.py --server.port=\$PORT --server.address=0.0.0.0" > Procfile
```

### Docker

```dockerfile
FROM python:3.10-slim
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py"]
```

## 📝 Notes

- All files are self-contained and deployment-ready
- No GUI dependencies included
- Optimized for web deployment
- Uses stable Python 3.10.12
- Total size: ~20MB (vs 100MB+ original)
