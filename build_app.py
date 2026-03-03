import PyInstaller.__main__
import os
import shutil

import sys

# Clean dist
if os.path.exists('dist'):
    shutil.rmtree('dist')
if os.path.exists('build'):
    shutil.rmtree('build')

# Define paths
ENTRY_POINT = os.path.join('src', 'main.py')
APP_NAME = 'Nexus Music Tag & Downloader'

# Determine Icon based on OS
if sys.platform == 'darwin':
    ICON_PATH = 'src/assets/icon.icns'
elif sys.platform == 'win32':
    ICON_PATH = 'src/assets/icon.ico'
else:
    ICON_PATH = 'src/assets/icon.png' # Fallback

# PyInstaller args
args = [
    ENTRY_POINT,
    '--name=' + APP_NAME,
    '--windowed', # No console
    '--noconfirm',
    '--clean',
    '--onedir',   # Standard App Bundle structure
    f'--icon={ICON_PATH}',
    '--add-data=src/assets:src/assets',
    # Recursively include packages if hidden imports are missed, 
    # but usually PyInstaller finds them.
    '--collect-all=mutagen',
    '--collect-all=yt_dlp',
]

print(f"Building {APP_NAME}...")
PyInstaller.__main__.run(args)

print("Build complete.")
if os.path.exists(f"dist/{APP_NAME}.app"):
    print(f"App is at: dist/{APP_NAME}.app")
else:
    print(f"Executable is at: dist/{APP_NAME}")
