@echo off
REM ============================================================
REM Kiro Intercepted - All-in-One Launcher
REM ============================================================
REM This script:
REM 1. Starts mitmproxy on dedicated port
REM 2. Launches Kiro with proxy configured
REM 3. Only Kiro traffic goes through proxy (system unaffected)
REM 4. Cleans up on exit
REM ============================================================

setlocal enabledelayedexpansion

set PROXY_PORT=99974
set SCRIPT_DIR=%~dp0

echo.
echo ============================================================
echo Launching Kiro with Interception
echo ============================================================
echo.
echo Configuration:
echo   - Proxy: 127.0.0.1:%PROXY_PORT%
echo   - Certificate validation: DISABLED
echo   - Only Kiro traffic is proxied
echo.
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python.
    pause
    exit /b 1
)

REM Check if mitmproxy is installed
python -c "import mitmproxy" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: mitmproxy not installed.
    echo Install with: pip install mitmproxy
    pause
    exit /b 1
)

echo [1/2] Starting mitmproxy on port %PROXY_PORT%...
echo.

REM Start mitmproxy in background
start "Kiro MITM Proxy" /MIN cmd /c "cd /d "%SCRIPT_DIR%frida-scripts" && python test_proxy.py %PROXY_PORT%"

REM Wait for proxy to start
echo Waiting for proxy to initialize...
timeout /t 3 /nobreak >nul

echo.
echo [2/2] Launching Kiro with interception enabled...
echo.
echo ============================================================
echo Kiro is now running with traffic interception
echo ============================================================
echo.
echo To view intercepted traffic:
echo   - Check the "Kiro MITM Proxy" window
echo   - Or run: python frida-scripts/view_traffic.py
echo.
echo To stop:
echo   - Close Kiro normally
echo   - Close the proxy window
echo.
echo Press any key to launch Kiro...
pause >nul

REM Set environment variables
set NODE_TLS_REJECT_UNAUTHORIZED=0
set ELECTRON_IGNORE_CERTIFICATE_ERRORS=1
set VSCODE_DEV=
set ELECTRON_RUN_AS_NODE=1

REM Launch Kiro with proxy
"%~dp0Kiro\Kiro.exe" "%~dp0Kiro\resources\app\out\cli.js" --ignore-certificate-errors --ignore-certificate-errors-spki-list --proxy-server="127.0.0.1:%PROXY_PORT%" %*

echo.
echo Kiro closed. Proxy is still running in background.
echo Close the "Kiro MITM Proxy" window to stop interception.
echo.

endlocal
