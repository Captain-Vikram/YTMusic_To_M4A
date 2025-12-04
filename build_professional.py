#!/usr/bin/env python3
"""
Professional Build Script for TrackOut
Creates optimized executables for both Console and GUI versions
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import time
import textwrap

# Application naming
APP_NAME = 'TrackOut'
GUI_EXE_NAME = f"{APP_NAME}_GUI"
CONSOLE_EXE_NAME = f"{APP_NAME}_Console"

def install_requirements():
    """Install all required packages including PyInstaller"""
    print("📦 Installing required packages...")
      
    packages = [
        "pyinstaller>=6.0.0",
        "yt-dlp>=2023.12.30",
        "mutagen>=1.47.0",
        "moviepy>=1.0.3",
        "requests>=2.31.0",
        "numpy>=1.21.0"
    ]
    
    # Install the packages one by one
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
    
    # Install PyQt5 separately with more detailed output
    print("   🔄 Installing PyQt5 (this may take a while)...")
    try:
        # First try to uninstall in case of corrupted installation
        subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", "PyQt5", "PyQt5-Qt5", "PyQt5-sip"],
            check=False, capture_output=True
        )
        
        # Now install PyQt5 with verbose output
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
    """Convert existing PNG icon to ICO format for executables"""
    try:
        from PIL import Image
        
        # Use the existing PNG icon
        # prefer package icon, fallback to gui/icon.png
        png_icon_path = None
        if os.path.exists('trackout/icon.png'):
            png_icon_path = 'trackout/icon.png'
        elif os.path.exists('gui/icon.png'):
            png_icon_path = 'gui/icon.png'
        else:
            png_icon_path = 'gui/icon.png'
        ico_icon_path = "app_icon.ico"
        
        if png_icon_path and os.path.exists(png_icon_path):
            # Load and convert PNG to ICO
            img = Image.open(png_icon_path)
            
            # Ensure it's in RGBA mode
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Save as ICO with multiple sizes
            img.save(ico_icon_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
            print(f"   ✅ Converted existing PNG icon to ICO: {ico_icon_path}")
            return ico_icon_path
        else:
            print(f"   ⚠️ PNG icon not found at {png_icon_path}")
            return None
            
    except Exception as e:
        print(f"   ⚠️ Could not convert icon: {e}")
        return None

def create_console_spec():
    """Create PyInstaller spec file for console version"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

    a = Analysis(
    ['trackout/core.py'],
    pathex=[],
    binaries=[],    datas=[
        ('trackout/icon.png', 'trackout'),
        ('trackout/gui_full.py', 'trackout'),
        ('trackout/__init__.py', 'trackout'),
        ('trackout/core.py', '.'),
        ('README.md', '.'),
        ('requirements.txt', '.')
    ],hiddenimports=[
        'yt_dlp',
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
        'PIL',
        'PIL.Image',
        'requests',
        'numpy',
        """
        Professional Build Script for TrackOut
        Creates optimized executables for both Console and GUI versions
        """
        'numpy.core',
        'numpy.core._multiarray_umath',
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
        'io'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'PyQt5.QtTest',
        'PyQt5.QtSql',
        'PyQt5.QtNetwork',
        'PyQt5.QtXml'
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
    name='{CONSOLE_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico' if os.path.exists('app_icon.ico') else None,
    version_file=None
)
'''
    
    # Replace placeholders and normalize indentation
    spec_content = spec_content.replace('{CONSOLE_NAME}', CONSOLE_EXE_NAME)
    # Normalize indentation: remove common 4-space prefix if present
    lines = spec_content.splitlines()
    normalized = []
    for line in lines:
        if line.startswith('    '):
            normalized.append(line[4:])
        else:
            normalized.append(line)
    spec_content = '\n'.join(normalized) + ('\n' if spec_content.endswith('\n') else '')
    with open('console.spec', 'w') as f:
        f.write(spec_content)
    
    print("   ✅ Created console.spec")

def create_gui_launcher():
    """Create a GUI launcher that uses the beautiful GUI"""
    launcher_content = '''#!/usr/bin/env python3
"""
GUI Launcher for TrackOut
"""

import sys
import os
from pathlib import Path
import traceback

# Add the project directory to the path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

def main():
    """Main launcher function"""
    try:
        # Import PyQt5 components
        from PyQt5.QtWidgets import QApplication, QDesktopWidget, QMessageBox
        from PyQt5.QtCore import Qt
        import logging
        
        # Setup basic logging for GUI mode (log to file)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('trackout.log'),
            ]
        )
        
        # Create application first
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(True)
        
        try:
            from trackout.gui_full import YouTubeMusicExtractorGUI
            
            # Create and show the main window
            window = YouTubeMusicExtractorGUI()
            
            # Center the window on screen
            desktop = QDesktopWidget()
            screen_rect = desktop.screenGeometry()
            window_rect = window.geometry()
            x = (screen_rect.width() - window_rect.width()) // 2
            y = (screen_rect.height() - window_rect.height()) // 2
            window.move(x, y)
            
            window.show()
            window.raise_()  # Bring to front
            window.activateWindow()  # Activate the window
            
            # Ensure window is visible and on top
            window.setWindowState(window.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
            window.setWindowFlags(window.windowFlags() | Qt.WindowStaysOnTopHint)
            window.show()  # Show again to ensure visibility
            
            # Run the application
            result = app.exec_()
            return result
            
        except Exception as gui_error:
            logging.error(f"Beautiful GUI failed: {gui_error}")
            app.quit()
            
            # Fallback to simple PyQt5 GUI
            app = QApplication(sys.argv)
            
            from PyQt5.QtWidgets import QMessageBox, QVBoxLayout, QWidget, QPushButton, QLineEdit, QLabel
              # Show error message first
            QMessageBox.critical(None, "GUI Error", 
                               f"Main GUI failed to load. Using simple interface."
                               f"Error: {str(gui_error)}"
                               f"Check 'trackout.log' for details.")
            
            # Create a simple input window
            widget = QWidget()
            widget.setWindowTitle("TrackOut - Simple GUI")
            widget.setGeometry(300, 300, 500, 200)
            widget.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
            
            layout = QVBoxLayout()
            
            # URL input
            url_label = QLabel("Enter YouTube URL:")
            layout.addWidget(url_label)
            
            url_input = QLineEdit()
            url_input.setPlaceholderText("Paste YouTube URL here...")
            layout.addWidget(url_input)
            
            # Download button
            def start_download():
                url = url_input.text().strip()
                if url:
                    # Import and call main with the URL
                    try:
                        import trackout.core as main
                        # Set the URL for main to use
                        import builtins
                        original_input = builtins.input
                        builtins.input = lambda prompt="": url if "URL" in prompt else ""
                        try:
                            main.main()
                        except:
                            pass
                        finally:
                            builtins.input = original_input
                        widget.close()
                    except Exception as e:
                        QMessageBox.critical(widget, "Error", f"Download failed: {e}")
                else:
                    QMessageBox.warning(widget, "Warning", "Please enter a YouTube URL")
            
            download_btn = QPushButton("Download")
            download_btn.clicked.connect(start_download)
            layout.addWidget(download_btn)
            
            widget.setLayout(layout)
            widget.show()
            widget.raise_()
            widget.activateWindow()
            
            sys.exit(app.exec_())
        
    except ImportError as e:
        # PyQt5 not available - show error and exit
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Missing Dependencies", 
                               f"PyQt5 not available: {e}"
                               f"Please use the Console version instead.")
            root.destroy()
        except:
            # No GUI available at all
            with open('gui_error.log', 'w') as f:
                f.write(f"GUI startup failed: PyQt5 not available: {e}")
                f.write("Please use the Console version instead.")
        
    except Exception as e:
        # Log other errors
        try:
            with open('gui_error.log', 'w') as f:
                f.write(f"GUI startup error: {e}")
                f.write("Please use the Console version instead.")
        except:
            pass

if __name__ == "__main__":
    main()
'''
    
    with open('gui_launcher.py', 'w') as f:
        f.write(launcher_content)
    
    print("   ✅ Created gui_launcher.py")

def create_gui_spec():
    """Create PyInstaller spec file for GUI version"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

    a = Analysis(
    ['trackout/gui_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('trackout/icon.png', 'trackout'),
        ('README.md', '.'),
        ('requirements.txt', '.')    ],    hiddenimports=[
        'yt_dlp',
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
        'PIL',
        'PIL.Image',
        'requests',
        'numpy',
        'numpy.core',
        'numpy.core._multiarray_umath',
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
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
        'trackout.core',
        'io'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'PyQt5.QtTest',
        'PyQt5.QtSql',
        'PyQt5.QtNetwork',
        'PyQt5.QtXml'
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
    [],    name='{GUI_NAME}',
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
    icon='app_icon.ico' if os.path.exists('app_icon.ico') else None,
    version_file=None
)
'''
    
    spec_content = spec_content.replace('{GUI_NAME}', GUI_EXE_NAME)
    # Normalize indentation: remove common 4-space prefix if present
    lines = spec_content.splitlines()
    normalized = []
    for line in lines:
        if line.startswith('    '):
            normalized.append(line[4:])
        else:
            normalized.append(line)
    spec_content = '\n'.join(normalized) + ('\n' if spec_content.endswith('\n') else '')
    with open('gui.spec', 'w') as f:
        f.write(spec_content)
    
    print("   ✅ Created gui.spec")

def fix_main_imports():
    """Fix missing imports in main.py"""
    print("🔧 Fixing main.py imports...")
    
    # Read the current main.py
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if imports are missing
    if 'import yt_dlp' not in content:
        # Add missing imports at the top
        imports_to_add = '''import yt_dlp
import os
import requests
import shutil
import threading
import time
import glob
'''
        
        # Find the first existing import and add before it
        lines = content.split('\n')
        insert_index = 0
        for i, line in enumerate(lines):
            if line.startswith('from ') or line.startswith('import '):
                insert_index = i
                break
        
        lines.insert(insert_index, imports_to_add)
        content = '\n'.join(lines)
        
        # Write back to file
        with open('main.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("   ✅ Added missing imports to main.py")

def build_executables():
    """Build both console and GUI executables"""
    print("🔨 Building executables...")
    
    # Clean previous builds
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # Build console version
    print("\n📦 Building Console Version...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "PyInstaller", 
            "--clean", 
            "console.spec"
        ], check=True, capture_output=True, text=True)
        print("   ✅ Console build completed!")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Console build failed: {e}")
        print(f"   Error output: {e.stderr}")
        return False
    
    # Build GUI version
    print("\n📦 Building GUI Version...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "PyInstaller", 
            "--clean", 
            "gui.spec"
        ], check=True, capture_output=True, text=True)
        print("   ✅ GUI build completed!")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ GUI build failed: {e}")
        print(f"   Error output: {e.stderr}")
        return False
    
    return True

def create_launcher_batch():
    """Create a launcher batch file"""
    batch_content = '''@echo off
title TrackOut Launcher
echo.
echo ================================
echo  TrackOut
echo ================================
echo.
echo Choose version to run:
echo [1] Console Version (Text-based, shows progress)
echo [2] GUI Version (Windowed interface, no console)
echo [3] Exit
echo.
set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" (
    echo.
    echo Starting Console Version...
    "TrackOut.exe"
) else if "%choice%"=="2" (
    echo.
    echo Starting GUI Version (no console window will appear)...
    start "" "TrackOut_GUI.exe"
    echo GUI started! Look for the application window.
    timeout /t 2 /nobreak >nul
    exit
) else if "%choice%"=="3" (
    echo.
    echo Goodbye!
    exit
) else (
    echo.
    echo Invalid choice. Starting Console Version...
    "TrackOut_Console.exe"
)

echo.
pause
'''
    
    with open('dist/Launch_TrackOut.bat', 'w') as f:
        f.write(batch_content)
    
    print("   ✅ Created launcher batch file")

def build_gui_only():
    """Build only the GUI executable"""
    print("🚀 TrackOut - GUI Only Build")
    print("=" * 50)
    
    # Change to project directory
    os.chdir(Path(__file__).parent)
    
    # Step 1: Install requirements
    if not install_requirements():
        print("❌ Failed to install requirements")
        return False
    
    # Step 2: Fix imports
    fix_main_imports()
    
    # Verify PyQt5 is working before proceeding
    print("\n🔍 Verifying PyQt5 installation...")
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import PyQt5.QtWidgets; print('PyQt5 verification successful')"],
            check=True, capture_output=True, text=True
        )
        print(f"   ✅ {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ PyQt5 verification failed: {e}")
        print(f"   Error output: {e.stderr}")
        print("   🔄 Attempting to reinstall PyQt5...")
        try:
            # Reinstall PyQt5 with more options
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--force-reinstall", "--no-cache-dir", "PyQt5>=5.15.10"],
                check=True
            )
            print("   ✅ PyQt5 reinstalled")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ PyQt5 reinstallation failed: {e}")
            return False
    
    # Step 3: Create icon
    icon_path = create_icon()
    
    # Step 4: Create GUI launcher and spec
    print("\n📝 Creating GUI build specifications...")
    create_gui_launcher()
    create_gui_spec()
    
    # Step 5: Clean previous builds
    print("\n🧹 Cleaning previous builds...")
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    # Step 6: Build GUI version only
    print("\n📦 Building GUI Version...")
    try:
        result = subprocess.run([
            sys.executable, "-m", "PyInstaller", 
            "--clean", 
            "gui.spec"
        ], check=True, capture_output=True, text=True)
        print("   ✅ GUI build completed!")
    except subprocess.CalledProcessError as e:
        print(f"   ❌ GUI build failed: {e}")
        print(f"   Error output: {e.stderr}")
        return False
    
    # Step 7: Cleanup build files
    print("\n🧹 Cleaning up build files...")
    cleanup_files = ['gui.spec', 'gui_launcher.py', 'build']
    if icon_path:
        cleanup_files.append(icon_path)
    
    for file in cleanup_files:
        try:
            if os.path.isfile(file):
                os.remove(file)
            elif os.path.isdir(file):
                shutil.rmtree(file)
        except:
            pass
    
    # Step 8: Show results
    print("\n" + "=" * 50)
    print("🎉 GUI BUILD COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    
    if os.path.exists('dist'):
        print("\n📁 Generated files:")
        for item in os.listdir('dist'):
            item_path = os.path.join('dist', item)
            if os.path.isfile(item_path):
                size_mb = os.path.getsize(item_path) / (1024 * 1024)
                print(f"   ✅ {item} ({size_mb:.1f} MB)")
            else:
                print(f"   📁 {item}/")
    
    print(f"\n🚀 GUI executable is ready: dist/TrackOut_GUI.exe")
    print("💡 The executable is fully self-contained and portable!")
    
    return True

def main():
    """Main build process"""
    print("🚀 TrackOut - Professional Build System")
    print("=" * 60)
    
    # Change to project directory
    os.chdir(Path(__file__).parent)
    
    # Step 1: Install requirements
    if not install_requirements():
        print("❌ Failed to install requirements")
        return False
    
    # Step 2: Fix imports
    fix_main_imports()
    
    # Step 3: Create icon
    icon_path = create_icon()
    
    # Step 4: Create launchers and specs
    print("\n📝 Creating build specifications...")
    create_gui_launcher()
    create_console_spec()
    create_gui_spec()
    
    # Step 5: Build executables
    success = build_executables()
    
    if success:
        # Step 6: Create launcher
        print("\n🎯 Creating launcher...")
        create_launcher_batch()
        
        # Step 7: Cleanup build files
        print("\n🧹 Cleaning up build files...")
        cleanup_files = ['console.spec', 'gui.spec', 'gui_launcher.py', 'build']
        if icon_path:
            cleanup_files.append(icon_path)
        
        for file in cleanup_files:
            try:
                if os.path.isfile(file):
                    os.remove(file)
                elif os.path.isdir(file):
                    shutil.rmtree(file)
            except:
                pass
        
        # Step 8: Show results
        print("\n" + "=" * 60)
        print("🎉 BUILD COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        if os.path.exists('dist'):
            print("\n📁 Generated files:")
            for item in os.listdir('dist'):
                item_path = os.path.join('dist', item)
                if os.path.isfile(item_path):
                    size_mb = os.path.getsize(item_path) / (1024 * 1024)
                    print(f"   ✅ {item} ({size_mb:.1f} MB)")
                else:
                    print(f"   📁 {item}/")
        
        print("\n🚀 Your executables are ready in the 'dist' folder!")
        print("   • Run 'Launch_TrackOut.bat' for easy access")
        print("   • Or run the executables directly")
        print("\n💡 The executables are fully self-contained and portable!")
        
        return True
    else:
        print("\n❌ Build failed. Check the error messages above.")
        return False

if __name__ == "__main__":
    try:
        # Check for command line arguments
        if len(sys.argv) > 1 and sys.argv[1] == "--gui-only":
            # Build GUI version only
            success = build_gui_only()
            if not success:
                sys.exit(1)
        else:
            success = main()
            if not success:
                sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Build interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Build error: {e}")
        sys.exit(1)
    
    print("\nPress Enter to exit...")
    input()
