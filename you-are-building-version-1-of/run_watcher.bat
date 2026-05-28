@echo off
cd /d %~dp0
if not exist .env copy .env.example .env
call .venv\Scripts\activate.bat
python -m social_video_formatter.workers.drive_watcher
