@echo off
REM ============================================================
REM Safe Proxy Test Setup
REM ============================================================
REM This script:
REM 1. Saves current proxy settings
REM 2. Enables proxy for testing
REM 3. Starts mitmproxy
REM 4. Restores original settings on exit
REM ============================================================

setlocal

echo.
echo ============================================================
echo Kiro Proxy Test - Safe Setup
echo ============================================================
echo.

REM Check if running as admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script requires administrator privileges
    echo Right-click and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo [1/4] Saving current proxy settings...
netsh winhttp show proxy > proxy_backup.txt
echo Saved to: proxy_backup.txt
echo.

echo [2/4] Enabling proxy (127.0.0.1:99974)...
netsh winhttp set proxy 127.0.0.1:99974
echo.

echo [3/4] Starting mitmproxy...
echo.
echo ============================================================
echo IMPORTANT: When you're done testing:
echo   1. Press Ctrl+C to stop mitmproxy
echo   2. This script will automatically restore your proxy settings
echo ============================================================
echo.
echo Starting in 3 seconds...
timeout /t 3 /nobreak >nul

REM Start Python proxy script
python test_proxy.py

REM This runs after Ctrl+C
echo.
echo.
echo [4/4] Restoring original proxy settings...
netsh winhttp reset proxy
echo.
echo ============================================================
echo Proxy settings restored - Internet should work normally now
echo ============================================================
echo.

pause
endlocal
