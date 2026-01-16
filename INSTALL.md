# 🔧 Installations-Anleitung (Windows)

## Schritt-für-Schritt Installation

### Schritt 1: Python-Pakete installieren

Öffne PowerShell/CMD im Scraper-Verzeichnis:

```bash
# Einzeln installieren (sicherer)
pip install playwright
pip install beautifulsoup4
pip install lxml
pip install httpx
pip install aiohttp
pip install rich
pip install click
pip install pyyaml
pip install python-dotenv
pip install tqdm
pip install validators
```

### Schritt 2: Playwright Browser installieren

**WICHTIG:** Nutze diesen Befehl statt `python scraper.py init`:

```bash
playwright install chromium
```

Falls das fehlschlägt, versuche:

```bash
python -m playwright install chromium
```

### Schritt 3: Testen

```bash
python scraper.py --help
```

Sollte jetzt funktionieren!

## Häufige Probleme

### "playwright: command not found"

Playwright ist nicht im PATH. Versuche:

```bash
python -m playwright install chromium
```

### "FileNotFoundError" beim Browser-Download

1. Prüfe Internetverbindung
2. Prüfe ob Antivirus den Download blockt
3. Versuche mit Administrator-Rechten

### Alles schlägt fehl

Nutze die Light-Version (ohne Playwright):
```bash
python scraper-light.py scrape "URL"
```

## Testen der Installation

```bash
# Hilfe anzeigen
python scraper.py --help

# Test-Scrape (zeigt nur was gefunden wird, lädt nicht herunter)
python scraper.py scrape "https://example.com" --dry-run
```

## Windows-spezifische Tipps

- Führe CMD/PowerShell als Administrator aus
- Deaktiviere temporär Antivirus für die Installation
- Stelle sicher dass Python im PATH ist
- Nutze Python 3.8 oder neuer
