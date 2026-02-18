@echo off
:: DarkPause - Silent launch with Administrator privileges
:: No terminal window stays open. Runs in background via pythonw.

:: Check if already admin
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :RUN
)

:: Elevate using VBScript (silent, reliable)
set "SCRIPT_DIR=%~dp0"
set "VBS=%temp%\darkpause_elevate.vbs"

echo Set UAC = CreateObject^("Shell.Application"^) > "%VBS%"
echo UAC.ShellExecute "pythonw.exe", """%SCRIPT_DIR%darkpause.py""", "%SCRIPT_DIR%", "runas", 0 >> "%VBS%"

cscript //nologo "%VBS%"
del "%VBS%" >nul 2>&1
exit /b

:RUN
cd /d "%~dp0"
start "" pythonw darkpause.py
exit /b
