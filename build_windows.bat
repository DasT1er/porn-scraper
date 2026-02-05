@echo off
REM Porn Scraper - Windows .exe Builder
REM Builds ONE single executable with everything included

echo ================================================================
echo   Porn Scraper - Windows .exe Builder
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

REM Run build script
python build.py

pause
