# Build Instructions for Windows 11

## Super Easy - Just 1 Step!

### Option 1: Double-Click (Easiest!)
```
Double-click: build_windows.bat
```

### Option 2: Command Prompt
```cmd
python build.py
```

That's it! Your .exe files will be in the `dist\` folder.

## What You Get

After building:
- `dist\scraper.exe` - Command-line version
- `dist\scraper_ui.exe` - Interactive UI version

## Important Notes

**For Distribution:**
Copy these 3 files to use anywhere:
- `dist\scraper.exe`
- `dist\scraper_ui.exe`
- `config.yaml`

**First-Time Setup:**
Users must install Playwright browsers once:
```cmd
pip install playwright
playwright install chromium
```

## Troubleshooting

**"Python not found":**
- Install Python from https://www.python.org/downloads/
- Make sure to check "Add Python to PATH" during installation

**Build fails:**
- Run: `pip install -r requirements.txt`
- Run: `pip install pyinstaller cffi`
- Then try again: `python build.py`

## That's All!

No complicated steps, no Docker, no Linux scripts needed.
Just run `build.py` and get your .exe files!
