#!/usr/bin/env python3
"""
Porn Scraper - FULLY PORTABLE Builder
Creates ONE .exe with Chromium bundled properly
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def print_header(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

def run_command(cmd, description):
    """Run command and show output"""
    print(f"\n{description}...")
    print("-" * 70)
    result = subprocess.run(cmd, shell=True)
    print("-" * 70)
    if result.returncode != 0:
        print(f"ERROR: {description} failed!")
        return False
    print(f"OK: {description} completed\n")
    return True

def main():
    print_header("Porn Scraper - Fully Portable Builder")
    print("This creates ONE executable with Chromium included")
    print("Final size: ~400 MB")
    print("Build time: 10-15 minutes\n")

    # Clean old builds
    print("Cleaning old builds...")
    for folder in ["build", "dist", "dist_portable"]:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"  Removed {folder}/")
    print("OK\n")

    # Step 1: Install all dependencies
    print_header("Step 1/4: Installing Dependencies")

    if not run_command(
        f"{sys.executable} -m pip install -r requirements.txt",
        "Installing requirements"
    ):
        return 1

    if not run_command(
        f"{sys.executable} -m pip install pyinstaller",
        "Installing PyInstaller"
    ):
        return 1

    # Step 2: Install Playwright and browsers
    print_header("Step 2/4: Installing Playwright Browsers")

    if not run_command(
        f"{sys.executable} -m pip install playwright",
        "Installing Playwright"
    ):
        return 1

    if not run_command(
        "playwright install chromium",
        "Downloading Chromium (~300 MB)"
    ):
        return 1

    # Step 3: Build the .exe
    print_header("Step 3/4: Building Executable")

    # Create build command
    build_cmd = f"""pyinstaller ^
        --onedir ^
        --name PornScraper ^
        --console ^
        --add-data "config.yaml;." ^
        --hidden-import playwright ^
        --hidden-import playwright.async_api ^
        --hidden-import bs4 ^
        --hidden-import yaml ^
        --hidden-import requests ^
        --hidden-import rich ^
        --hidden-import questionary ^
        --hidden-import PIL ^
        --hidden-import tqdm ^
        --collect-all playwright ^
        --collect-all rich ^
        --collect-all questionary ^
        scraper_ui.py"""

    if not run_command(build_cmd, "Building with PyInstaller"):
        return 1

    # Step 4: Copy Chromium to the build
    print_header("Step 4/4: Adding Chromium Browser")

    # Find Playwright's Chromium
    playwright_cache = Path.home() / "AppData" / "Local" / "ms-playwright"
    chromium_dirs = list(playwright_cache.glob("chromium-*"))

    if not chromium_dirs:
        print("ERROR: Chromium not found!")
        print(f"Searched in: {playwright_cache}")
        return 1

    chromium_src = chromium_dirs[0]
    print(f"Found Chromium: {chromium_src}")

    # Copy to dist folder
    chromium_dest = Path("dist") / "PornScraper" / "playwright_browsers" / "chromium"
    print(f"Copying to: {chromium_dest}")

    chromium_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(chromium_src, chromium_dest, dirs_exist_ok=True)
    print("OK: Chromium copied\n")

    # Create launcher script
    print("Creating launcher...")
    launcher_content = """@echo off
cd /d "%~dp0PornScraper"
set PLAYWRIGHT_BROWSERS_PATH=%~dp0PornScraper\\playwright_browsers
PornScraper.exe
pause
"""

    launcher_path = Path("dist") / "START_PornScraper.bat"
    launcher_path.write_text(launcher_content)
    print("OK: Launcher created\n")

    # Create README
    readme_content = """
PORN SCRAPER - PORTABLE VERSION

EINFACH STARTEN:
================
Doppelklick auf: START_PornScraper.bat

INHALT:
=======
PornScraper/
  - PornScraper.exe          (Hauptprogramm)
  - playwright_browsers/     (Chromium Browser)
  - _internal/               (Alle Dependencies)

START_PornScraper.bat        (Starter)

WEITERGEBEN:
============
Einfach den kompletten "dist" Ordner kopieren und weitergeben!
Kein Setup, keine Installation nötig!

GRÖSSE:
=======
Ca. 400-500 MB (wegen Chromium Browser)

VIEL ERFOLG! 🎉
"""

    readme_path = Path("dist") / "README.txt"
    readme_path.write_text(readme_content, encoding='utf-8')
    print("OK: README created\n")

    # Show results
    print_header("Build Complete!")

    total_size = sum(f.stat().st_size for f in Path("dist").rglob('*') if f.is_file())
    total_size_mb = total_size / (1024 * 1024)

    print(f"✓ Portable version created in: dist\\")
    print(f"✓ Total size: {total_size_mb:.1f} MB")
    print()
    print("=" * 70)
    print("HOW TO USE:")
    print("=" * 70)
    print()
    print("1. Go to: dist\\")
    print("2. Double-click: START_PornScraper.bat")
    print("3. Use the program!")
    print()
    print("=" * 70)
    print("TO DISTRIBUTE:")
    print("=" * 70)
    print()
    print("- Zip the 'dist' folder")
    print("- Send to anyone")
    print("- They unzip and run START_PornScraper.bat")
    print("- Everything works immediately!")
    print()

    input("\nPress Enter to exit...")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nBuild cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
