@echo off
REM Porn Scraper - PORTABLE Version Builder
REM Creates fully portable version with Chromium included

echo ================================================================
echo   Porn Scraper - PORTABLE Version Builder
echo ================================================================
echo.
echo This creates a FULLY PORTABLE version:
echo   - Chromium browser included
echo   - NO installations needed
echo   - Final size: 300-500 MB
echo.
echo ================================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not installed!
    echo.
    echo Install from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo Python OK
echo.

REM Run portable build script
python build_portable.py

pause
