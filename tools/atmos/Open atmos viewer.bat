@echo off
rem Opens the atmosphere viewer (no server needed). Rebuild it with: python tools\atmos\build_viewer.py
start "" "%~dp0..\..\docs\atmos_viewer.html"
