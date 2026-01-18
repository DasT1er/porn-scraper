@echo off
REM Windows .exe Builder Batch Script
REM Run this on Windows to create .exe files

echo ================================================================
echo   Windows .exe Builder for Porn Scraper
echo ================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed!
    echo.
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo Python is installed
echo.

REM Run the Python build script
python build.py

echo.
echo ================================================================
pause
