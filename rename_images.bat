@echo off
setlocal enabledelayedexpansion

echo ========================================
echo    Bilder-Umbenennung Tool
echo ========================================
echo.

REM Eingabe des neuen Namens
set /p newname="Geben Sie den neuen Dateinamen ein (z.B. Bild): "

REM Pruefen ob ein Name eingegeben wurde
if "%newname%"=="" (
    echo Kein Name eingegeben. Abbruch.
    pause
    exit /b
)

echo.
echo Bilder werden umbenannt nach: %newname%_001, %newname%_002, etc.
echo.
echo Moechten Sie fortfahren? (J/N)
set /p confirm=

if /i not "%confirm%"=="J" (
    echo Abgebrochen.
    pause
    exit /b
)

REM Zaehler initialisieren
set count=0

echo.
echo Starte Umbenennung...
echo.

REM Schleife durch alle Bilddateien
for %%f in (*.jpg *.jpeg *.png *.gif *.bmp *.webp *.JPG *.JPEG *.PNG *.GIF *.BMP *.WEBP) do (
    set /a count+=1

    REM Formatiere Nummer mit fuehrenden Nullen (3 Stellen)
    set "num=00!count!"
    set "num=!num:~-3!"

    REM Ermittle Dateiendung
    set "ext=%%~xf"

    REM Umbenennen
    ren "%%f" "%newname%_!num!!ext!"
    echo Umbenannt: %%f --^> %newname%_!num!!ext!
)

echo.
echo ========================================
echo Fertig! !count! Dateien umbenannt.
echo ========================================
pause
