@echo off
REM Porn Scraper - Fully Portable Builder
REM Creates ONE .exe with Chromium bundled

echo ================================================================
echo   Porn Scraper - Fully Portable Builder
echo ================================================================
echo.
echo This creates a FULLY PORTABLE version:
echo   - ONE executable
echo   - Chromium browser included
echo   - NO installation needed
echo   - Final size: ~400 MB
echo.
echo Build time: 10-15 minutes
echo.
echo ================================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not installed!
    echo.
    pause
    exit /b 1
)

echo Python OK
echo.

REM Run build script
python build_fully_portable.py

echo.
echo ================================================================
pause
