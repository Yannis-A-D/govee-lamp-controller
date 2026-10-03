@echo off
title Govee Lamp Controller
cd /d "%~dp0"
echo Starting Govee Lamp Web Controller...
py server.py
pause
