@echo off
setlocal
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0registryRepair.ps1" %*
exit /b %ERRORLEVEL%
