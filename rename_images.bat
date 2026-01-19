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
echo Starte Umbenennung (Schritt 1: Temporaere Namen)...
echo.

REM Schritt 1: Alle Dateien zu temporaeren Namen umbenennen
for %%f in (*.jpg *.jpeg *.png *.gif *.bmp *.webp *.JPG *.JPEG *.PNG *.GIF *.BMP *.WEBP) do (
    set /a count+=1
    set "num=00000!count!"
    set "num=!num:~-6!"
    set "ext=%%~xf"
    ren "%%f" "temp_!num!!ext!"
)

echo Schritt 1 abgeschlossen: !count! Dateien temporaer umbenannt.
echo.
echo Starte Schritt 2: Finale Umbenennung...
echo.

REM Zaehler zuruecksetzen
set count=0

REM Schritt 2: Temporaere Dateien zu finalen Namen umbenennen
for %%f in (temp_*.jpg temp_*.jpeg temp_*.png temp_*.gif temp_*.bmp temp_*.webp temp_*.JPG temp_*.JPEG temp_*.PNG temp_*.GIF temp_*.BMP temp_*.WEBP) do (
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
