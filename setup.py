from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="yt-music-extractor",
    version="1.0.0",
    author="Vighnesh Kontham",
    author_email="your.email@example.com",
    description="Extract music from YouTube with proper metadata and album art",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/youtube-music-extractor",
    packages=find_packages(),
    py_modules=["main", "config"],
    install_requires=requirements,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Internet :: WWW/HTTP",
    ],
    python_requires=">=3.7",
    keywords="youtube, music, download, metadata, album art, yt-dlp, parallel processing",
    entry_points={
        "console_scripts": [
            "yt-music-extractor=main:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/youtube-music-extractor/issues",
        "Source": "https://github.com/yourusername/youtube-music-extractor",
    },
)