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
    print(f"\nBuilding {exe_name}...")
    print("This may take 2-5 minutes, please wait...\n")

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

    # Run PyInstaller with LIVE output
    print("PyInstaller output:")
    print("-" * 70)
    try:
        result = subprocess.run(cmd, check=True)
        print("-" * 70)
        print(f"\nSUCCESS: {exe_name}.exe built!\n")
        return True
    except subprocess.CalledProcessError as e:
        print("-" * 70)
        print(f"\nERROR building {exe_name}: Build failed (exit code {e.returncode})")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
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
            print(f"  Removed {folder}/")

    # Remove old spec files created by previous builds
    for spec in Path(".").glob("*.spec"):
        spec.unlink()
        print(f"  Removed {spec.name}")

    print("Clean complete\n")

    # Build executables
    print_header("Building Executables")
    print("\nIMPORTANT: Each build takes 2-5 minutes!")
    print("You will see PyInstaller output below.\n")

    success = True

    # Build CLI version
    if not build_exe_direct("scraper_v2.py", "scraper"):
        success = False

    # Build UI version
    if not build_exe_direct("scraper_ui.py", "scraper_ui"):
        success = False

    # Show results
    print_header("Build Complete!")

    if success:
        dist_path = Path("dist")

        if dist_path.exists():
            print("Executables created in: dist\\\n")

            for exe_file in sorted(dist_path.glob("*.exe")):
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
            input("\nPress Enter to exit...")
            return 0
        else:
            print("ERROR: dist folder not created")
            input("\nPress Enter to exit...")
            return 1
    else:
        print("Some builds failed. Check errors above.")
        input("\nPress Enter to exit...")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nBuild cancelled by user")
        input("\nPress Enter to exit...")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
