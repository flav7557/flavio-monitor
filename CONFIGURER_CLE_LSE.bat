@echo off
setlocal
title Configuration London Strategic Edge
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\configure_key.ps1"
if errorlevel 1 pause
endlocal
