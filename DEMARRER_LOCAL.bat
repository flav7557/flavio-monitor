@echo off
setlocal
title Flavio Market Terminal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_local.ps1"
if errorlevel 1 (
  echo.
  echo Le demarrage a echoue. Consulte le message ci-dessus.
  pause
)
endlocal
