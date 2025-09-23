@echo off
echo 🎵 YouTube Music Extractor - Streamlit Deployment
echo ================================================
echo.
echo Testing deployment folder...
echo.

cd /d "%~dp0"

echo 📁 Current directory: %CD%
echo.

echo 📋 Files in deployment folder:
dir /b
echo.

echo 🔍 Checking Python...
python --version
echo.

echo 📦 Installing requirements...
pip install -r requirements.txt
echo.

echo 🚀 Starting Streamlit app...
echo.
echo 🌐 The app will open in your browser at: http://localhost:8501
echo 🛑 Press Ctrl+C to stop the server
echo.
streamlit run streamlit_app.py