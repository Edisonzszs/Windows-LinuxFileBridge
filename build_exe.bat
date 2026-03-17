@echo off
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --windowed --name WindowsLinuxFileBridge wsl_file_bridge_gui.py
