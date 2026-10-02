@echo off
title Squall Cove
cd /d "%~dp0"

rem Pick whichever Python launcher this machine has
where py >nul 2>nul
if %errorlevel%==0 (set "PYCMD=py") else (set "PYCMD=python")

echo.
echo   SQUALL COVE
echo   -----------
echo   Opening in a dedicated Chrome window on your NVIDIA GPU.
echo.
echo   Keep THIS window open while you play.
echo   Close it (or press Ctrl+C) to stop.
echo.

%PYCMD% "%~dp0serve.py" 8771 --chrome
