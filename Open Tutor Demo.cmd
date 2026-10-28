@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python tools\tutor_demo.py
) else (
  py -3.12 tools\tutor_demo.py
)
if errorlevel 1 echo Tutor demo could not start. Read the message above.
pause
