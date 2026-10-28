@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python tools\verify_local.py all
) else (
  py -3.12 tools\verify_local.py all
)
if errorlevel 1 echo Some checks failed or could not run. See .local\verification and COMPLETE-LOCAL-TEST.md.
pause
