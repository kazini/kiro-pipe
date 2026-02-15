@echo off
REM ============================================================
REM Emergency Proxy Disable
REM ============================================================
REM Run this if your internet stops working after testing
REM ============================================================

echo.
echo ============================================================
echo Disabling Proxy Settings
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

echo Resetting proxy settings...
netsh winhttp reset proxy

echo.
echo ============================================================
echo Done! Your internet should work normally now.
echo ============================================================
echo.

REM Show current status
echo Current proxy status:
netsh winhttp show proxy

echo.
pause
