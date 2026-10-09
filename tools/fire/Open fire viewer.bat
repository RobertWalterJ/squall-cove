@echo off
rem Opens the baked-fire viewer (no server needed). Rebuild it with: python tools\fire\build_viewer.py
start "" "%~dp0..\..\docs\fire_viewer.html"
