#!/usr/bin/env python3
"""
Specialized Build Script for TrackOut GUI Launcher
Packages only the GUI launcher and its direct dependencies into a standalone executable
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Application naming
APP_NAME = 'TrackOut_GUI'

def install_requirements():
    """Install required packages for GUI launcher"""
    print("📦 Installing required packages for GUI...")
      
    packages = [
        "pyinstaller>=6.0.0",
        "yt-dlp>=2023.12.30",
        "mutagen>=1.47.0",
        "moviepy>=1.0.3",
        "requests>=2.31.0",
        "numpy>=1.21.0",
        "Pillow>=10.0.0"
    ]
    
    # Install packages
    for package in packages:
        try:
            print(f"   🔄 Installing {package}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", package],
                check=True, capture_output=True, text=True
            )
            print(f"   ✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Failed to install {package}: {e}")
            print(f"   Error output: {e.stderr}")
            return False
    
    # Install PyQt5 with special handling
    print("   🔄 Installing PyQt5 (this may take a while)...")
    try:
        # Uninstall any existing PyQt5 to avoid conflicts
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", "PyQt5", "PyQt5-Qt5", "PyQt5-sip"],
            check=False, capture_output=True
        )
        
        # Install PyQt5
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "PyQt5>=5.15.10"],
            check=True, capture_output=True, text=True
        )
        print("   ✅ PyQt5>=5.15.10 installed successfully")
        
        # Verify PyQt5 installation
        verify = subprocess.run(
            [sys.executable, "-c", "import PyQt5.QtWidgets; print('PyQt5 verification successful')"],
            check=True, capture_output=True, text=True
        )
        print(f"   ✅ {verify.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed to install PyQt5: {e}")
        print(f"   Error output: {e.stderr}")
        return False
    
    return True

def create_icon():
    """Convert PNG icon to ICO format for the executable"""
    try:
        from PIL import Image
        
        # Look for the icon file
        icon_paths = [
            'trackout/icon.png',
            'gui/icon.png'
        ]
        
        png_icon_path = None
        for path in icon_paths:
            if os.path.exists(path):
                png_icon_path = path
                break
        
        if png_icon_path:
            ico_icon_path = "gui_launcher_icon.ico"
            
            # Load and convert PNG to ICO
            img = Image.open(png_icon_path)
            
            # Ensure it's in RGBA mode
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Save as ICO with multiple sizes
            img.save(ico_icon_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
            print(f"   ✅ Converted PNG icon to ICO: {ico_icon_path}")
            return ico_icon_path
        else:
            print(f"   ⚠️ PNG icon not found in common locations")
            return None
            
    except ImportError:
        print("   ⚠️ Pillow not installed, cannot convert icon")
        return None
    except Exception as e:
        print(f"   ⚠️ Could not convert icon: {e}")
        return None

def create_gui_launcher_spec(icon_path=None):
    """Create PyInstaller spec file for GUI launcher"""
    project_dir = Path(__file__).parent
    
    # Determine data files to include - only add files that exist
    datas = []
    
    # Add trackout package files (check each one exists)
    trackout_files = [
        'trackout/gui_full.py',
        'trackout/core.py',
        'trackout/gui_launcher.py',
        'trackout/__init__.py',
    ]
    
    for file in trackout_files:
        if os.path.exists(file):
            datas.append((file, 'trackout'))
    
    # Add icon if it exists
    if os.path.exists('trackout/icon.png'):
        datas.append(('trackout/icon.png', 'trackout'))
    elif os.path.exists('trackout/icon.jpg'):
        datas.append(('trackout/icon.jpg', 'trackout'))
    elif os.path.exists('gui/icon.png'):
        datas.append(('gui/icon.png', 'gui'))
    
    # Add documentation files if they exist
    if os.path.exists('README.md'):
        datas.append(('README.md', '.'))
    if os.path.exists('requirements.txt'):
        datas.append(('requirements.txt', '.'))
    
    # Hidden imports needed for the GUI launcher
    hiddenimports = [
        # Core dependencies
        'yt_dlp',
        'yt_dlp.extractor',
        'yt_dlp.downloader',
        'mutagen',
        'mutagen.mp4',
        'mutagen.flac',
        'mutagen.id3',
        'moviepy',
        'moviepy.audio.io.AudioFileClip',
        'moviepy.audio.fx',
        'moviepy.video.fx',
        'moviepy.audio.fx.all',
        'moviepy.video.fx.all',
        # Pillow plugins (ensure JPEG/WEBP open works in exe)
        'PIL',
        'PIL.Image',
        'PIL.ImageFile',
        'PIL.ImageFilter',
        'PIL.ImageOps',
        'PIL.ImageChops',
        'PIL.ImageQt',
        'PIL.JpegImagePlugin',
        'PIL.PngImagePlugin',
        'PIL.GifImagePlugin',
        'PIL.BmpImagePlugin',
        'PIL.WebPImagePlugin',
        'PIL.TiffImagePlugin',
        'PIL._imaging',
        'PIL._webp',
        'requests',
        'numpy',
        'numpy.core',
        'numpy.core._multiarray_umath',
        # PyQt5 modules
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.sip',
        # Standard library
        'concurrent.futures',
        'threading',
        'json',
        'pathlib',
        'urllib.parse',
        'subprocess',
        'imageio',
        'imageio_ffmpeg',
        'decorator',
        'proglog',
        'tqdm',
        'io',
        'importlib',
        'importlib.util',
        # Trackout modules
        'trackout',
        'trackout.core',
        'trackout.gui_full',
        'trackout.gui_launcher',
    ]
    
    # Determine icon value for spec file
    if icon_path and os.path.exists(icon_path):
        icon_value = f"'{icon_path}'"
    else:
        icon_value = 'None'
    
    # Write spec file
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None

a = Analysis(
    ['trackout/gui_launcher.py'],
    pathex=['{project_dir.as_posix()}'],
    binaries=[],
    datas={repr(datas)},
    hiddenimports={repr(hiddenimports)},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'PyQt5.QtTest',
        'PyQt5.QtSql',
        'PyQt5.QtNetwork',
        'PyQt5.QtXml',
        'PyQt5.QtBluetooth',
        'PyQt5.QtDBus',
        'PyQt5.QtDesigner',
        'PyQt5.QtHelp',
        'PyQt5.QtLocation',
        'PyQt5.QtMultimedia',
        'PyQt5.QtMultimediaWidgets',
        'PyQt5.QtNfc',
        'PyQt5.QtOpenGL',
        'PyQt5.QtPositioning',
        'PyQt5.QtQml',
        'PyQt5.QtQuick',
        'PyQt5.QtQuickWidgets',
        'PyQt5.QtSensors',
        'PyQt5.QtSerialPort',
        'PyQt5.QtSvg',
        'PyQt5.QtWebChannel',
        'PyQt5.QtWebEngine',
        'PyQt5.QtWebEngineCore',
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtWebSockets',
        'PyQt5.QtX11Extras',
        'PyQt5.QtXmlPatterns',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{APP_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon={icon_value},
    version_file=None
)
'''
    
    with open('gui_launcher.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("   ✅ Created gui_launcher.spec")

def build_gui_launcher():
    """Build the GUI launcher executable"""
    print("🔨 Building GUI launcher executable...")
    
    # Clean previous builds
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # Build GUI launcher
    print("\n📦 Building GUI Launcher...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "PyInstaller", 
            "--clean", 
            "gui_launcher.spec"
        ], check=True, capture_output=True, text=True)
        print("   ✅ GUI launcher build completed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ GUI launcher build failed: {e}")
        print(f"   Error output: {e.stderr}")
        if e.stdout:
            print(f"   Standard output: {e.stdout}")
        return False

def create_launcher_batch():
    """Create a simple batch file to launch the GUI"""
    batch_content = f'''@echo off
title {APP_NAME} Launcher
echo.
echo ================================
echo  TrackOut GUI Launcher
echo ================================
echo.
echo Starting TrackOut GUI...
echo.

start "" "{APP_NAME}.exe"

echo.
echo GUI started! Look for the application window.
echo This window will close in 3 seconds...
timeout /t 3 /nobreak >nul
exit
'''
    
    dist_path = Path('dist')
    if dist_path.exists():
        with open(dist_path / 'Launch_TrackOut_GUI.bat', 'w') as f:
            f.write(batch_content)
        
        print("   ✅ Created launcher batch file")

def main():
    """Main build process for GUI launcher"""
    print("🚀 TrackOut - GUI Launcher Build System")
    print("=" * 60)
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Step 1: Install requirements
    print("\n📦 Step 1: Installing dependencies...")
    if not install_requirements():
        print("❌ Failed to install requirements")
        return False
    
    # Step 2: Verify PyQt5
    print("\n🔍 Step 2: Verifying PyQt5 installation...")
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import PyQt5.QtWidgets; print('PyQt5 OK')"],
            check=True, capture_output=True, text=True
        )
        print(f"   ✅ {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ PyQt5 verification failed: {e}")
        return False
    
    # Step 3: Create icon
    print("\n🎨 Step 3: Creating application icon...")
    icon_path = create_icon()
    
    # Step 4: Create spec file
    print("\n📝 Step 4: Creating build specification...")
    create_gui_launcher_spec(icon_path)
    
    # Step 5: Build executable
    print("\n🔨 Step 5: Building executable...")
    success = build_gui_launcher()
    
    if success:
        # Step 6: Create launcher batch
        print("\n🎯 Step 6: Creating launcher batch file...")
        create_launcher_batch()
        
        # Step 7: Cleanup build files
        print("\n🧹 Step 7: Cleaning up temporary files...")
        cleanup_files = ['gui_launcher.spec', 'build']
        if icon_path and os.path.exists(icon_path):
            cleanup_files.append(icon_path)
        
        for file in cleanup_files:
            try:
                if os.path.isfile(file):
                    os.remove(file)
                    print(f"   ✅ Removed {file}")
                elif os.path.isdir(file):
                    shutil.rmtree(file)
                    print(f"   ✅ Removed {file}/")
            except Exception as e:
                print(f"   ⚠️ Could not remove {file}: {e}")
        
        # Step 8: Show results
        print("\n" + "=" * 60)
        print("🎉 GUI LAUNCHER BUILD COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        if os.path.exists('dist'):
            print("\n📁 Generated files in 'dist' folder:")
            for item in sorted(os.listdir('dist')):
                item_path = os.path.join('dist', item)
                if os.path.isfile(item_path):
                    size_mb = os.path.getsize(item_path) / (1024 * 1024)
                    print(f"   ✅ {item} ({size_mb:.1f} MB)")
                else:
                    print(f"   📁 {item}/")
        
        print(f"\n🚀 GUI executable is ready: dist/{APP_NAME}.exe")
        print("💡 Run 'Launch_TrackOut_GUI.bat' or the executable directly!")
        print("💡 The executable is fully self-contained and portable!")
        
        return True
    else:
        print("\n❌ Build failed. Check the error messages above.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Build interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Build error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\nPress Enter to exit...")
    input()
