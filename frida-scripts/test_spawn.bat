@echo off
REM Quick test script for Frida spawn gating
REM This will spawn Kiro with hooks to bypass anti-debug

echo ========================================
echo Frida Spawn Gating Test
echo ========================================
echo.
echo This will:
echo 1. Auto-detect Kiro.exe location
echo 2. Spawn Kiro with Frida hooks
echo 3. Monitor for child processes
echo 4. Auto-inject hooks into networking subprocess
echo.
echo Press Ctrl+C to stop monitoring
echo ========================================
echo.

python attach.py --spawn --hook kiro_api_hook

pause
