from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="yt-music-extractor",
    version="1.0.2",
    author="Vighnesh Kontham",
    author_email="vighneshkontham@gmail.com",
    description="Download music from YouTube with proper metadata and album art, featuring parallel processing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Captain-Vikram/YTMusic_To_M4A",
    packages=find_packages(),
    py_modules=["main", "config"],
    install_requires=[
        "setuptools>=67.7.2",
        "yt-dlp>=2023.3.4",
        "moviepy>=1.0.3",
        "mutagen>=1.46.0",
        "pillow>=9.4.0",
        "requests>=2.28.2",
    ],
    entry_points={
        "console_scripts": [
            "yt-music-extractor=main:main",
            "ytme=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    keywords="youtube, music, download, metadata, album art, yt-dlp",
    license="MIT",
)