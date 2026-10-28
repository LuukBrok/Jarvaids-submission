@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "tools\stop_jarvaids.ps1"
pause
