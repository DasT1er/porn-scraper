#!/usr/bin/env python3
"""
Porn Scraper - Windows .exe Builder
Builds ONE single executable
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_header(text):
    """Print header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

def check_and_install_deps():
    """Check and install build dependencies"""
    print("Checking dependencies...\n")

    # Check PyInstaller
    try:
        import PyInstaller
        print("OK PyInstaller installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "cffi"])
        print("OK PyInstaller installed")

    # Install all requirements
    if os.path.exists("requirements.txt"):
        print("\nInstalling dependencies from requirements.txt...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("OK All dependencies installed")

    print()

def clean_old_builds():
    """Remove old build artifacts"""
    print("Cleaning old builds...")

    for folder in ["build", "dist", "__pycache__"]:
        if os.path.exists(folder):
            import shutil
            shutil.rmtree(folder)
            print(f"  Removed {folder}/")

    # Remove old spec files
    for spec in Path(".").glob("*.spec"):
        spec.unlink()
        print(f"  Removed {spec.name}")

    print("OK Clean complete\n")

def build_single_exe():
    """Build single .exe file"""
    print_header("Building PornScraper.exe")
    print("Building ONE portable .exe file...")
    print("This will take 3-5 minutes.\n")

    # PyInstaller command - SINGLE FILE
    cmd = [
        "pyinstaller",
        "--onefile",                          # Single .exe file
        "--name", "PornScraper",              # Name
        "--console",                          # Keep console for now

        # Include data files
        "--add-data", "config.yaml;.",

        # Hidden imports - ALL dependencies
        "--hidden-import", "playwright",
        "--hidden-import", "playwright.async_api",
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

        # Collect all submodules
        "--collect-all", "playwright",
        "--collect-all", "rich",
        "--collect-all", "questionary",

        # Main script
        "scraper_ui.py"
    ]

    print("PyInstaller output:")
    print("-" * 70)

    try:
        result = subprocess.run(cmd, check=True)
        print("-" * 70)
        print("\nOK Build successful!\n")
        return True
    except subprocess.CalledProcessError as e:
        print("-" * 70)
        print(f"\nERROR Build failed (exit code {e.returncode})\n")
        return False

def show_results():
    """Show build results"""
    print_header("Build Complete!")

    dist_path = Path("dist")

    if not dist_path.exists():
        print("ERROR: dist/ folder not created!")
        return False

    exe_files = list(dist_path.glob("*.exe"))
    if not exe_files:
        print("ERROR: No .exe file created!")
        return False

    print("SUCCESS! Your executable is ready:\n")

    for exe_file in sorted(exe_files):
        size = exe_file.stat().st_size / (1024 * 1024)
        print(f"   File: {exe_file.name}")
        print(f"   Size: {size:.1f} MB")
        print(f"   Path: {exe_file.absolute()}\n")

    print("=" * 70)
    print("HOW TO USE:")
    print("=" * 70)
    print("\n1. Go to folder: dist\\")
    print("2. Double-click: PornScraper.exe")
    print("3. Follow the menu\n")

    print("=" * 70)
    print("FIRST TIME SETUP:")
    print("=" * 70)
    print("\nBefore using, install Playwright browsers:")
    print("  pip install playwright")
    print("  playwright install chromium\n")
    print("This is needed only once!\n")

    return True

def main():
    print_header("Porn Scraper - Windows .exe Builder")

    # Check platform
    if platform.system() != "Windows":
        print("WARNING: Not on Windows!")
        print("Will create executable for your current platform.\n")
    else:
        print(f"Platform: Windows")
        print(f"Python: {sys.version.split()[0]}\n")

    # Install dependencies
    check_and_install_deps()

    # Clean
    clean_old_builds()

    # Build
    if not build_single_exe():
        print("\nERROR: Build failed!")
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
