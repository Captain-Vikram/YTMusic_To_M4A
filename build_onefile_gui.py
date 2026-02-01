"""Build a single-file executable for the TrackOut GUI launcher using PyInstaller.
Run with: python build_onefile_gui.py
"""
import os
import shutil
from pathlib import Path

import PyInstaller.__main__
from PIL import Image

PROJECT = Path(__file__).resolve().parent
BUILD_DIR = PROJECT / "build"
DIST_DIR = PROJECT / "dist"


def _collect_datas():
    datas = []

    def add_if_exists(src_rel: str, dest: str):
        src = PROJECT / src_rel
        if src.exists():
            datas.append(f"{src};{dest}")

    add_if_exists("trackout/gui_full.py", "trackout")
    add_if_exists("trackout/core.py", "trackout")
    add_if_exists("trackout/gui_launcher.py", "trackout")
    add_if_exists("trackout/__init__.py", "trackout")
    add_if_exists("trackout/icon.png", "trackout")
    add_if_exists("trackout/icon.jpg", "trackout")
    add_if_exists("README.md", ".")

    return datas


def _resolve_icon():
    """Return an ICO path for the executable icon if possible."""
    ico = PROJECT / "trackout" / "icon.ico"
    if ico.exists():
        return ico

    # Convert a PNG or JPG to ICO if found
    for candidate in (PROJECT / "trackout" / "icon.png", PROJECT / "trackout" / "icon.jpg"):
        if candidate.exists():
            try:
                img = Image.open(candidate)
                # Save alongside build script so path is stable
                tmp_ico = PROJECT / "trackout" / "icon_converted.ico"
                img.save(tmp_ico, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
                return tmp_ico
            except Exception:
                return None
    return None


def build():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    datas = _collect_datas()

    # Detect local ffmpeg.exe in common locations and include it in datas so
    # the onefile bundle contains ffmpeg for runtime embedding of cover art.
    ffmpeg_candidates = [
        PROJECT / 'ffmpeg.exe',
        PROJECT / 'ffmpeg' / 'ffmpeg.exe',
        PROJECT / 'ffmpeg' / 'bin' / 'ffmpeg.exe',
        PROJECT / 'bin' / 'ffmpeg.exe',
        PROJECT / 'ffmpeg' / 'win64' / 'ffmpeg.exe',
    ]
    ffmpeg_path = None
    for cand in ffmpeg_candidates:
        if cand.exists():
            ffmpeg_path = cand
            break

    if ffmpeg_path:
        # Target inside bundle as folder 'ffmpeg' so runtime path is predictable
        datas.append(f"{ffmpeg_path};ffmpeg")
        print(f"   ✅ Including ffmpeg for bundling: {ffmpeg_path}")
    else:
        print("   ⚠️ No local ffmpeg.exe found in project; embedding skipped")

    hidden_imports = [
        "yt_dlp",
        "yt_dlp.extractor",
        "yt_dlp.downloader",
        "mutagen",
        "mutagen.mp4",
        "mutagen.flac",
        "mutagen.id3",
        "moviepy",
        "moviepy.audio.io.AudioFileClip",
        "moviepy.audio.fx",
        "moviepy.video.fx",
        "moviepy.audio.fx.all",
        "moviepy.video.fx.all",
        "PIL",
        "PIL.Image",
        "PIL.ImageFile",
        "PIL.ImageFilter",
        "PIL.ImageOps",
        "PIL.ImageChops",
        "PIL.ImageQt",
        "PIL.JpegImagePlugin",
        "PIL.PngImagePlugin",
        "PIL.GifImagePlugin",
        "PIL.BmpImagePlugin",
        "PIL.WebPImagePlugin",
        "PIL.TiffImagePlugin",
        "PIL._imaging",
        "PIL._webp",
        "requests",
        "numpy",
        "numpy.core",
        "numpy.core._multiarray_umath",
        "PyQt5",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "PyQt5.sip",
        "imageio",
        "imageio_ffmpeg",
        "decorator",
        "proglog",
        "tqdm",
        "trackout",
        "trackout.core",
        "trackout.gui_full",
        "trackout.gui_launcher",
    ]

    icon_path = _resolve_icon()

    cmd = [
        "--clean",
        "--onefile",
        "--noconsole",
        "--name",
        "TrackOut_GUI",
        "--collect-all",
        "trackout",
    ]

    if icon_path:
        cmd.extend(["--icon", str(icon_path)])

    for data in datas:
        cmd.extend(["--add-data", data])

    for mod in hidden_imports:
        cmd.extend(["--hidden-import", mod])

    cmd.append(str(PROJECT / "trackout/gui_launcher.py"))

    print("Running PyInstaller with:")
    for part in cmd:
        print(f"  {part}")

    PyInstaller.__main__.run(cmd)


if __name__ == "__main__":
    build()
