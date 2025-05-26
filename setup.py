from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("//")]

setup(
    name="yt-music-extractor",
    version="1.0.0",
    author="Vighnesh Kontham",
    author_email="vighneshkontham@gmail.com",  # Replace with your email
    description="Download music from YouTube with proper metadata and album art",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Captain-Vikram/YTMusic_To_M4A.git",  # Replace with your GitHub repo
    packages=find_packages(),
    py_modules=["main", "config"],
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "yt-music-extractor=main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)