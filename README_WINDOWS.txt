╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║        Windows .exe Builder - Anleitung für Windows 11           ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝


📋 VORAUSSETZUNGEN
════════════════════════════════════════════════════════════════════

1. Python muss installiert sein
   → Download: https://www.python.org/downloads/
   → Wichtig: "Add Python to PATH" anhaken bei Installation!

2. Alle Dependencies installieren:
   → Öffne Command Prompt (CMD) oder PowerShell
   → Gehe zum Projekt-Ordner: cd C:\Pfad\zum\porn-scraper
   → Führe aus: pip install -r requirements.txt


🚀 .exe DATEIEN BAUEN - SUPER EINFACH!
════════════════════════════════════════════════════════════════════

METHODE 1 (Empfohlen):
----------------------
→ Doppelklick auf: build_windows.bat

Das war's! Das Programm macht alles automatisch:
  ✓ Installiert PyInstaller (falls nötig)
  ✓ Baut scraper.exe
  ✓ Baut scraper_ui.exe
  ✓ Zeigt dir wo die Dateien sind


METHODE 2 (Kommandozeile):
--------------------------
→ Öffne Command Prompt im Projekt-Ordner
→ Führe aus: python build.py

Gleicher Effekt wie Methode 1, nur mit mehr Ausgaben!


📁 WO SIND DIE .EXE DATEIEN?
════════════════════════════════════════════════════════════════════

Nach dem Build findest du die Dateien in:

    dist\scraper.exe       ← Kommandozeilen-Version
    dist\scraper_ui.exe    ← Interaktive UI-Version


📦 DISTRIBUTION (Weitergabe)
════════════════════════════════════════════════════════════════════

Wenn du die .exe an andere weitergeben willst, kopiere:

  1. dist\scraper.exe
  2. dist\scraper_ui.exe
  3. config.yaml

Diese 3 Dateien können dann überall ausgeführt werden!


⚠️  WICHTIG FÜR ENDBENUTZER
════════════════════════════════════════════════════════════════════

Wer die .exe benutzt, muss vorher einmalig Playwright installieren:

    pip install playwright
    playwright install chromium

Das muss nur einmal gemacht werden, nicht bei jedem Start!


🎯 NUTZUNG DER .EXE
════════════════════════════════════════════════════════════════════

Command-Line Version (scraper.exe):
-----------------------------------
→ Öffne CMD im Ordner mit scraper.exe
→ Einzelne Gallery: scraper.exe https://multporn.net/comics/...
→ Mit Optionen: scraper.exe --mode browser --output Downloads URL

Interactive UI Version (scraper_ui.exe):
---------------------------------------
→ Doppelklick auf scraper_ui.exe
→ Folge dem interaktiven Menü
→ Super einfach!


🔧 PROBLEME?
════════════════════════════════════════════════════════════════════

"Python not found":
→ Python ist nicht installiert oder nicht im PATH
→ Neu installieren mit "Add to PATH" Option!

"PyInstaller not found":
→ Normal! build_windows.bat installiert es automatisch
→ Oder manuell: pip install pyinstaller

Build schlägt fehl:
→ Prüfe ob alle requirements installiert sind
→ pip install -r requirements.txt
→ pip install pyinstaller cffi


════════════════════════════════════════════════════════════════════
Viel Erfolg! 🚀
════════════════════════════════════════════════════════════════════
