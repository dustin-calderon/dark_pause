@echo off
:: DarkPause - Install/Uninstall Auto-Start
:: Creates a Windows Task Scheduler task that runs DarkPause
:: at user logon with Administrator privileges (no UAC prompt).

set TASK_NAME=DarkPause
set SCRIPT_DIR=%~dp0

:: Detect pythonw full path
set PYTHONW_PATH=pythonw.exe
for /f "tokens=*" %%i in ('where pythonw.exe 2^>nul') do set PYTHONW_PATH=%%i

if "%1"=="uninstall" goto :UNINSTALL

:: ─── INSTALL ───
echo ========================================
echo   DarkPause - Auto-Start Installer
echo ========================================
echo.

:: Check admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Run this script as Administrator.
    echo Right-click install.bat - "Run as administrator"
    pause
    exit /b 1
)

:: Delete existing task if any
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: Create scheduled task
schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "\"%PYTHONW_PATH%\" \"%SCRIPT_DIR%darkpause.py\"" ^
    /sc ONLOGON ^
    /rl HIGHEST ^
    /delay 0000:30 ^
    /f

if %errorLevel% == 0 (
    echo.
    echo ========================================
    echo   SUCCESS! DarkPause will auto-start.
    echo.
    echo   Task: %TASK_NAME%
    echo   Python: %PYTHONW_PATH%
    echo   Script: %SCRIPT_DIR%darkpause.py
    echo ========================================
) else (
    echo.
    echo ERROR: Failed to create scheduled task.
)

pause
exit /b

:: ─── UNINSTALL ───
:UNINSTALL
echo ========================================
echo   DarkPause - Full Uninstall
echo ========================================

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Run as Administrator.
    pause
    exit /b 1
)

:: Remove scheduled task
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

if %errorLevel% == 0 (
    echo   [OK] Auto-start task removed.
) else (
    echo   [--] Task not found or already removed.
)

:: Remove DarkPause firewall rules
echo.
echo   Removing DarkPause firewall rules...
netsh advfirewall firewall delete rule name="DarkPause-DNS-Lock" >nul 2>&1
echo   [OK] DNS lock rule removed.
netsh advfirewall firewall delete rule name="DarkPause-DoT-Lock" >nul 2>&1
echo   [OK] DoT lock rule removed.

echo.
echo ========================================
echo   DarkPause fully uninstalled.
echo ========================================

pause
exit /b

