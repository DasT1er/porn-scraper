#!/usr/bin/env python3
"""
Simple Windows .exe builder
Works on Windows 11
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_header(text):
    """Print fancy header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

def check_pyinstaller():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        return True
    except ImportError:
        return False

def install_pyinstaller():
    """Install PyInstaller"""
    print("Installing PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "cffi"])
    print("PyInstaller installed successfully\n")

def build_exe_direct(script_name, exe_name):
    """Build executable directly without spec file"""
    print(f"Building {exe_name}...")

    # Build command
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name", exe_name,
        "--add-data", "config.yaml;.",
        "--hidden-import", "playwright.async_api",
        "--hidden-import", "bs4",
        "--hidden-import", "yaml",
        "--hidden-import", "rich",
        "--hidden-import", "PIL",
        "--hidden-import", "tqdm",
    ]

    # Add questionary for UI version
    if "ui" in script_name:
        cmd.extend(["--hidden-import", "questionary"])

    cmd.append(script_name)

    # Run PyInstaller
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"SUCCESS: {exe_name}.exe built\n")
        return True
    else:
        print(f"ERROR building {exe_name}:")
        print(result.stderr)
        return False

def main():
    print_header("Windows .exe Builder")

    # Check platform
    if platform.system() != "Windows":
        print("WARNING: You are not on Windows!")
        print("This will create executables for your current platform only.\n")
    else:
        print("Platform: Windows")
        print("Python:", sys.version.split()[0], "\n")

    # Check PyInstaller
    if not check_pyinstaller():
        print("PyInstaller not found")
        response = input("Install PyInstaller now? [Y/n]: ").strip().lower()
        if response in ['', 'y', 'yes', 'j', 'ja']:
            install_pyinstaller()
        else:
            print("Cannot continue without PyInstaller")
            return 1
    else:
        print("PyInstaller is installed\n")

    # Clean old builds
    print("Cleaning old builds...")
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            import shutil
            shutil.rmtree(folder)

    # Remove old spec files created by previous builds
    for spec in Path(".").glob("*.spec"):
        if spec.name not in ["scraper.spec", "scraper_ui.spec", "scraper_v2.spec"]:
            spec.unlink()

    print("Clean complete\n")

    # Build executables
    print_header("Building Executables")

    success = True
    success = build_exe_direct("scraper_v2.py", "scraper") and success
    success = build_exe_direct("scraper_ui.py", "scraper_ui") and success

    # Show results
    print_header("Build Complete!")

    if success:
        dist_path = Path("dist")

        if dist_path.exists():
            print("Executables created in: dist\\\n")

            for exe_file in sorted(dist_path.glob("*")):
                if exe_file.is_file():
                    size = exe_file.stat().st_size / (1024 * 1024)
                    print(f"   {exe_file.name:<20} {size:>6.1f} MB")

            print("\n" + "=" * 70)
            print("SUCCESS!")
            print("=" * 70)
            print("\nTo distribute, copy these files:")
            print("   - dist\\scraper.exe")
            print("   - dist\\scraper_ui.exe")
            print("   - config.yaml")

            if platform.system() == "Windows":
                print("\nIMPORTANT: Users must install Playwright browsers once:")
                print("   pip install playwright")
                print("   playwright install chromium")

            print("")
            return 0
        else:
            print("ERROR: dist folder not created")
            return 1
    else:
        print("Some builds failed. Check errors above.")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nBuild cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
