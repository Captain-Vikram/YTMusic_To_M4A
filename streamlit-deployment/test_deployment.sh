#!/bin/bash
echo "🎵 YouTube Music Extractor - Streamlit Deployment"
echo "================================================"
echo ""

echo "Testing deployment folder..."
echo ""

echo "📁 Current directory: $(pwd)"
echo ""

echo "📋 Files in deployment folder:"
ls -la
echo ""

echo "🔍 Checking Python..."
python3 --version
echo ""

echo "📦 Installing requirements..."
pip3 install -r requirements.txt
echo ""

echo "🚀 Starting Streamlit app..."
echo ""
echo "🌐 The app will open in your browser at: http://localhost:8501"
echo "🛑 Press Ctrl+C to stop the server"
echo ""
streamlit run streamlit_app.py