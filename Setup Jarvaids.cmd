@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python tools\local_test.py setup
) else (
  py -3.12 tools\local_test.py setup
)
if errorlevel 1 echo Setup failed. Read the error above.
pause
