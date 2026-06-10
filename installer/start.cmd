@echo off
chcp 65001 >nul
setlocal
set "SCRIPT_DIR=%~dp0"
where pwsh.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  set "PS_EXE=pwsh.exe"
) else (
  set "PS_EXE=powershell.exe"
)
"%PS_EXE%" -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Start-XianyuDocker.ps1" %*
exit /b %ERRORLEVEL%
