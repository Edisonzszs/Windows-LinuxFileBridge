@echo off
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --windowed --icon assets\app_icon.ico --name WindowsLinuxFileBridge wsl_file_bridge_gui.py
