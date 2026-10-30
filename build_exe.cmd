@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_exe.ps1"
if errorlevel 1 (
    echo.
    echo Falha ao criar o executavel. Consulte a mensagem acima.
    pause
    exit /b 1
)
echo.
pause
