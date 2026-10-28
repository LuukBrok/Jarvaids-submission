@echo off
cd /d "%~dp0"
echo Choosing a photograph sends the whole sanitised image to Anthropic to find and read its notes.
echo It uses the private project API key in .env and may incur API charges.
echo Audio and speaker profiles stay local. See COMPLETE-LOCAL-TEST.md for the full trial.
where py >nul 2>nul
if errorlevel 1 (
  python tools\local_test.py start --language en --photo-reader claude
) else (
  py -3.12 tools\local_test.py start --language en --photo-reader claude
)
if errorlevel 1 echo Start failed. Read the error above.
pause
