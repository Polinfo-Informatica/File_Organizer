@echo off
setlocal
cd /d "%~dp0"
python -X utf8 "%~dp0clean_duplicate_videos.py" --apply
pause
