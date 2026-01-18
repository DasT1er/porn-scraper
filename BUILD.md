# Build Instructions

## Quick Start - Automatic Build

### Option 1: Windows Users (Easiest!)

Double-click `build_windows.bat` or run in Command Prompt:
```cmd
build_windows.bat
```

This will automatically:
- Install PyInstaller if needed
- Build both executables
- Show you where the .exe files are

### Option 2: Any Platform (Python Script)

Run the universal build script:
```bash
python build.py
```

Works on Windows, Linux, and Mac!

### Option 3: Linux/Mac to Windows (Docker Required)

Build Windows .exe on Linux/Mac using Docker:
```bash
./build_windows_exe.sh
```

This creates Windows executables in `windows_build/` folder.

## Manual Build (Advanced)

If you prefer to build manually:

### Prerequisites

```bash
pip install -r requirements.txt
pip install pyinstaller
```

### Building on Windows (for .exe files)

```bash
pyinstaller scraper.spec
pyinstaller scraper_ui.spec
```

The executables will be in `dist/scraper.exe` and `dist/scraper_ui.exe`.

### Building on Linux/Mac

```bash
pyinstaller scraper.spec
pyinstaller scraper_ui.spec
```

The executables will be in `dist/scraper` and `dist/scraper_ui`.

### Important Notes

- **Playwright**: After building, you must install Playwright browsers:
  ```bash
  playwright install chromium
  ```
  This must be done on each system where you run the executable.

- **config.yaml**: The executable includes `config.yaml`, but you can override it by placing a `config.yaml` file in the same directory as the executable.

- **Cross-platform**: PyInstaller builds for the current platform only. To create Windows .exe files, you must build on Windows. To create Linux executables, build on Linux.

### Using the Executables

**Command-line version (`scraper`):**
```bash
# Scrape a single gallery
./scraper URL

# With options
./scraper URL --mode browser --output ./downloads
```

**Interactive UI version (`scraper_ui`):**
```bash
# Launch interactive menu
./scraper_ui
```

### Troubleshooting

If the executable fails to run:

1. Make sure Playwright browsers are installed: `playwright install chromium`
2. Check that `config.yaml` is in the same directory
3. Run with `--help` to see available options
4. On Linux, make sure the file is executable: `chmod +x scraper`
