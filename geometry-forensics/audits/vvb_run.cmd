@echo off
set PYTHON="%LOCALAPPDATA%\Programs\Python\Python313\python.exe"

cd /d "%~dp0"

%PYTHON% vvb_animate260112.py

pause
