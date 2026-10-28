@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python tools\local_test.py start --language en
) else (
  py -3.12 tools\local_test.py start --language en
)
if errorlevel 1 echo Start failed. Read the error above.
pause
