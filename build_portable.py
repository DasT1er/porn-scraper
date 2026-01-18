#!/usr/bin/env python3
"""
Porn Scraper - PORTABLE .exe Builder
Creates a fully portable version with Chromium included
NO installations needed!
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def print_header(text):
    """Print header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

def check_and_install_deps():
    """Install ALL dependencies"""
    print("Installing ALL dependencies (this will take a few minutes)...\n")

    # Install requirements
    if os.path.exists("requirements.txt"):
        print("Installing from requirements.txt...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("OK\n")

    # Install PyInstaller
    print("Installing PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "cffi"])
    print("OK\n")

    # Install Playwright and browsers
    print("Installing Playwright browsers (this downloads ~300 MB)...")
    print("This is needed to bundle Chromium!\n")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
    subprocess.check_call(["playwright", "install", "chromium"])
    print("OK Playwright and Chromium installed\n")

def get_playwright_browser_path():
    """Find Playwright's Chromium installation"""
    print("Locating Playwright Chromium...")

    # Try to find Playwright cache directory
    possible_paths = [
        Path.home() / ".cache" / "ms-playwright",  # Linux
        Path.home() / "AppData" / "Local" / "ms-playwright",  # Windows
        Path.home() / "Library" / "Caches" / "ms-playwright",  # Mac
    ]

    for path in possible_paths:
        if path.exists():
            chromium_dirs = list(path.glob("chromium-*"))
            if chromium_dirs:
                print(f"Found Chromium at: {chromium_dirs[0]}")
                return chromium_dirs[0]

    print("WARNING: Could not find Playwright Chromium!")
    print("The portable version may not work without it.\n")
    return None

def clean_old_builds():
    """Clean old builds"""
    print("Cleaning old builds...")

    for folder in ["build", "dist_portable", "__pycache__"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"  Removed {folder}/")

    for spec in Path(".").glob("*.spec"):
        spec.unlink()
        print(f"  Removed {spec.name}")

    print("OK\n")

def build_portable_exe():
    """Build portable version"""
    print_header("Building Portable PornScraper")
    print("Creating portable version with Chromium included...")
    print("Build time: 5-10 minutes\n")

    # PyInstaller command - DIRECTORY mode for easier browser bundling
    cmd = [
        "pyinstaller",
        "--onedir",                           # Create directory (not single file)
        "--name", "PornScraper",
        "--console",

        # Include data
        "--add-data", "config.yaml;.",

        # Hidden imports
        "--hidden-import", "playwright",
        "--hidden-import", "playwright.async_api",
        "--hidden-import", "playwright.sync_api",
        "--hidden-import", "playwright._impl._driver",
        "--hidden-import", "bs4",
        "--hidden-import", "yaml",
        "--hidden-import", "requests",
        "--hidden-import", "rich",
        "--hidden-import", "rich.console",
        "--hidden-import", "rich.panel",
        "--hidden-import", "rich.table",
        "--hidden-import", "rich.prompt",
        "--hidden-import", "questionary",
        "--hidden-import", "PIL",
        "--hidden-import", "tqdm",
        "--hidden-import", "click",

        # Collect everything from Playwright
        "--collect-all", "playwright",
        "--collect-all", "rich",
        "--collect-all", "questionary",

        # Main script
        "scraper_ui.py"
    ]

    print("PyInstaller output:")
    print("-" * 70)

    try:
        subprocess.run(cmd, check=True)
        print("-" * 70)
        print("\nOK Build successful!\n")
        return True
    except subprocess.CalledProcessError as e:
        print("-" * 70)
        print(f"\nERROR Build failed (exit code {e.returncode})\n")
        return False

def create_portable_package():
    """Create portable package with browser"""
    print_header("Creating Portable Package")

    dist_dir = Path("dist") / "PornScraper"
    if not dist_dir.exists():
        print("ERROR: Build directory not found!")
        return False

    # Create portable directory
    portable_dir = Path("dist_portable")
    portable_dir.mkdir(exist_ok=True)

    print("Copying application files...")
    shutil.copytree(dist_dir, portable_dir / "PornScraper", dirs_exist_ok=True)
    print("OK\n")

    # Copy Chromium browser
    chromium_path = get_playwright_browser_path()
    if chromium_path and chromium_path.exists():
        print("Copying Chromium browser (this may take a few minutes)...")
        browser_dest = portable_dir / "PornScraper" / "_internal" / "playwright" / "chromium"
        browser_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(chromium_path, browser_dest, dirs_exist_ok=True)
        print("OK Chromium copied\n")
    else:
        print("WARNING: Chromium not copied - portable version may not work!\n")

    # Copy config
    if Path("config.yaml").exists():
        shutil.copy("config.yaml", portable_dir / "PornScraper" / "config.yaml")
        print("OK config.yaml copied\n")

    # Create start script
    create_start_script(portable_dir)

    # Create README
    create_readme(portable_dir)

    return True

def create_start_script(portable_dir):
    """Create convenient start script"""
    print("Creating start script...")

    # Windows batch file
    bat_content = """@echo off
cd /d "%~dp0PornScraper"
PornScraper.exe
pause
"""
    bat_file = portable_dir / "START_PornScraper.bat"
    bat_file.write_text(bat_content)
    print("OK Created START_PornScraper.bat\n")

def create_readme(portable_dir):
    """Create README for portable version"""
    readme_content = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║     PORN SCRAPER - PORTABLE VERSION                             ║
║     Komplett eigenständig - keine Installation nötig!           ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝


✅ WIE STARTEN:
═══════════════════════════════════════════════════════════════════

Doppelklick auf: START_PornScraper.bat

→ Das Programm startet automatisch
→ Folge dem interaktiven Menü
→ Fertig!


📁 WAS IST DRIN:
═══════════════════════════════════════════════════════════════════

PornScraper/
  ├── PornScraper.exe        - Hauptprogramm
  ├── _internal/             - Alle Libraries und Dependencies
  │   └── playwright/        - Chromium Browser (komplett)
  └── config.yaml            - Konfiguration

START_PornScraper.bat        - Einfacher Start
README.txt                   - Diese Datei


🚀 FEATURES:
═══════════════════════════════════════════════════════════════════

✓ Komplett portable - läuft überall
✓ Chromium Browser inklusive
✓ Keine Installation nötig
✓ Keine Playwright-Installation nötig
✓ Einfach kopieren und nutzen


📦 WEITERGEBEN:
═══════════════════════════════════════════════════════════════════

Einfach den kompletten Ordner kopieren und weitergeben!

Der Empfänger kann sofort loslegen - keine Installation nötig!


💡 TIPPS:
═══════════════════════════════════════════════════════════════════

- Die config.yaml kann angepasst werden
- Downloads landen standardmäßig im downloads/ Ordner
- Light Mode funktioniert ohne Browser
- Browser Mode nutzt den inkludierten Chromium


🔧 PROBLEME?
═══════════════════════════════════════════════════════════════════

Antivirus blockiert:
  → Antivirus-Ausnahme für den Ordner erstellen
  → Windows Defender: "Zugriff zulassen"

Programm startet nicht:
  → Als Administrator ausführen
  → Dateien nicht direkt von USB-Stick starten
  → Erst auf Festplatte kopieren

Browser funktioniert nicht:
  → Prüfen ob PornScraper/_internal/playwright/ existiert
  → Neu entpacken falls Dateien fehlen


═══════════════════════════════════════════════════════════════════
                    Viel Erfolg! 🎉
═══════════════════════════════════════════════════════════════════
"""
    readme_file = portable_dir / "README.txt"
    readme_file.write_text(readme_content, encoding='utf-8')
    print("OK Created README.txt\n")

def show_results():
    """Show final results"""
    print_header("Build Complete!")

    portable_dir = Path("dist_portable")

    if not portable_dir.exists():
        print("ERROR: Portable directory not created!")
        return False

    # Calculate total size
    total_size = sum(f.stat().st_size for f in portable_dir.rglob('*') if f.is_file())
    total_size_mb = total_size / (1024 * 1024)

    print("SUCCESS! Portable version ready:\n")
    print(f"   Location: {portable_dir.absolute()}")
    print(f"   Total Size: {total_size_mb:.1f} MB")
    print()

    print("=" * 70)
    print("PORTABLE PACKAGE CONTENTS:")
    print("=" * 70)
    print("\n  START_PornScraper.bat  - Double-click to start")
    print("  README.txt             - Instructions")
    print("  PornScraper/           - Application folder")
    print("    ├── PornScraper.exe")
    print("    ├── _internal/       - All dependencies")
    print("    └── config.yaml\n")

    print("=" * 70)
    print("HOW TO USE:")
    print("=" * 70)
    print("\n1. Copy the 'dist_portable' folder anywhere")
    print("2. Double-click: START_PornScraper.bat")
    print("3. Use the program!\n")

    print("=" * 70)
    print("TO DISTRIBUTE:")
    print("=" * 70)
    print("\n- Zip the 'dist_portable' folder")
    print("- Send to anyone")
    print("- They just unzip and run START_PornScraper.bat")
    print("- NO installations needed!\n")

    print("✓ Completely portable")
    print("✓ Chromium browser included")
    print("✓ Works anywhere on Windows\n")

    return True

def main():
    print_header("Porn Scraper - PORTABLE Builder")
    print("This creates a FULLY PORTABLE version")
    print("Final size: ~300-500 MB")
    print("NO installations needed for end users!\n")

    if platform.system() != "Windows":
        print("WARNING: Not on Windows!")
        print("Portable version is for Windows only.\n")

    # Confirm
    print("This will:")
    print("  1. Install all dependencies")
    print("  2. Download Chromium (~300 MB)")
    print("  3. Build the application")
    print("  4. Create portable package\n")

    response = input("Continue? [Y/n]: ").strip().lower()
    if response and response not in ['y', 'yes', 'j', 'ja']:
        print("Cancelled.")
        return 0

    # Install dependencies and browsers
    check_and_install_deps()

    # Clean
    clean_old_builds()

    # Build
    if not build_portable_exe():
        print("\nERROR: Build failed!")
        input("\nPress Enter to exit...")
        return 1

    # Create portable package
    if not create_portable_package():
        print("\nERROR: Failed to create portable package!")
        input("\nPress Enter to exit...")
        return 1

    # Show results
    if not show_results():
        input("\nPress Enter to exit...")
        return 1

    input("\nPress Enter to exit...")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nBuild cancelled")
        input("\nPress Enter to exit...")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
