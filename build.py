#!/usr/bin/env python3
"""
Simple cross-platform build script for creating Windows executables
Works on Windows, Linux, and Mac
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
    print("📦 Installing PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller", "cffi"])
    print("✓ PyInstaller installed\n")

def build_exe(spec_file, name):
    """Build executable from spec file"""
    print(f"🔨 Building {name}...")

    # Run PyInstaller
    result = subprocess.run(
        ["pyinstaller", "--clean", spec_file],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"✓ {name} built successfully\n")
        return True
    else:
        print(f"✗ Failed to build {name}")
        print(result.stderr)
        return False

def main():
    print_header("Windows .exe Builder for Porn Scraper")

    # Detect platform
    current_os = platform.system()
    print(f"Platform: {current_os}")
    print(f"Python: {sys.version.split()[0]}\n")

    if current_os == "Windows":
        print("✓ Running on Windows - will create Windows .exe files")
        exe_extension = ".exe"
    else:
        print("⚠️  Running on {0} - executables will be for {0} only".format(current_os))
        print("   To build Windows .exe, run this script on Windows")
        print("   Or use: ./build_windows_exe.sh (requires Docker)\n")
        exe_extension = ""

    # Check PyInstaller
    if not check_pyinstaller():
        print("⚠️  PyInstaller not found")
        response = input("Install PyInstaller now? [Y/n]: ").strip().lower()
        if response in ['', 'y', 'yes']:
            install_pyinstaller()
        else:
            print("Cannot continue without PyInstaller")
            return 1
    else:
        print("✓ PyInstaller is installed\n")

    # Build executables
    print_header("Building Executables")

    success = True
    success = build_exe("scraper.spec", "scraper (CLI version)") and success
    success = build_exe("scraper_ui.spec", "scraper_ui (Interactive UI)") and success

    # Show results
    print_header("Build Complete!")

    if success:
        dist_path = Path("dist")

        print("📁 Executables created in: dist/\n")

        for exe_file in dist_path.glob("*"):
            if exe_file.is_file():
                size = exe_file.stat().st_size / (1024 * 1024)  # MB
                print(f"   {exe_file.name:<20} {size:>6.1f} MB")

        print("\n" + "=" * 70)
        print("✅ SUCCESS!")
        print("=" * 70)
        print(f"\n📦 To distribute, copy these files:")
        print(f"   - dist/scraper{exe_extension}")
        print(f"   - dist/scraper_ui{exe_extension}")
        print(f"   - config.yaml")

        if current_os == "Windows":
            print(f"\n⚠️  Important: Users must install Playwright browsers:")
            print(f"   pip install playwright")
            print(f"   playwright install chromium")

        print("")
        return 0
    else:
        print("❌ Some builds failed. Check errors above.")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)
