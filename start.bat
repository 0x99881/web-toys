@echo off
setlocal

cd /d "%~dp0"

python --version >nul 2>nul
if errorlevel 1 (
  echo Python was not found.
  echo Run "python --version" in a terminal first.
  pause
  exit /b 1
)

python -u scripts\serve.py
