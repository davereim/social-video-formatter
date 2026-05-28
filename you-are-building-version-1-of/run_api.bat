@echo off
cd /d %~dp0

echo Starting Social Video Formatter API...

if not exist .venv\Scripts\python.exe (
  echo ERROR: Virtual environment not found.
  echo Please run setup first or contact me and I will recreate it.
  pause
  exit /b 1
)

if not exist .env (
  copy .env.example .env >nul
)

.venv\Scripts\python -m uvicorn social_video_formatter.main:app --host 127.0.0.1 --port 8000 --reload

if errorlevel 1 (
  echo.
  echo API exited with an error.
  pause
)
