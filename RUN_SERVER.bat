@echo off
cd /d "%~dp0"
echo Starting Brain Computer System Server...
echo.
echo Server will send 8-channel EEG simulated data to Unity at 30Hz
echo.
".\.venv\Scripts\python.exe" server/main.py
pause
