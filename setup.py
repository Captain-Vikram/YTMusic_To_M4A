from setuptools import setup, find_packages
import sys

# Check Python version
if sys.version_info < (3, 7):
    sys.exit('Python 3.7 or higher is required.')

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements from requirements.txt
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith('#')]

setup(
    name="yt-music-extractor",
    version="1.0.3",  # Increment version for the fixes
    author="Vighnesh Kontham",
    author_email="vighneshkontham@gmail.com",
    description="Download music from YouTube with proper metadata and album art, featuring parallel processing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Captain-Vikram/YTMusic_To_M4A",
    packages=find_packages(),
    py_modules=["main", "config"],
    install_requires=requirements,  # Read from requirements.txt
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
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.7",
    keywords="youtube, music, download, metadata, album art, yt-dlp",
    license="MIT",
    include_package_data=True,
    zip_safe=False,
)