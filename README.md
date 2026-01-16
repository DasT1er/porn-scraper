# 🎯 Intelligent Gallery Scraper

Ein intelligenter, automatischer Scraper für Bildergalerien und Comics mit schönem Terminal-UI.

## ✨ Features

- 🤖 **Automatische Galerie-Erkennung** - Findet Galerien ohne manuelle Konfiguration
- 🎨 **Schönes Rich UI** - Farben, Fortschrittsbalken, Live-Statistiken
- 📄 **Multi-Page Support** - Automatisches Laden aller Seiten mit Paginierung
- 🧠 **Smart Filtering** - Ignoriert Werbung, Thumbnails und UI-Elemente
- 📦 **Batch Processing** - Mehrere Galerien aus einer Liste herunterladen
- 🔄 **Retry Logic** - Automatische Wiederholung bei Fehlern
- ⚡ **Concurrent Downloads** - Schneller paralleler Download
- 🖼️ **Image Validation** - Filtert nach Größe und Auflösung
- 🎭 **Playwright Support** - Funktioniert mit allen Webseiten (auch JavaScript-heavy)

## 🚀 Installation

### 1. Python-Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 2. Playwright-Browser installieren

```bash
python scraper.py init
```

Oder manuell:
```bash
playwright install chromium
```

## 📖 Verwendung

### Einzelne Galerie scrapen

```bash
python scraper.py scrape "https://example.com/gallery/12345"
```

Mit custom Output-Verzeichnis:
```bash
python scraper.py scrape "https://example.com/gallery/12345" --output ./my-downloads
```

### Mehrere Galerien (Batch Mode)

1. Erstelle eine Datei `urls.txt` mit URLs (eine pro Zeile):
```text
https://example.com/gallery/1
https://example.com/gallery/2
https://example.com/gallery/3
```

2. Führe den Batch-Scraper aus:
```bash
python scraper.py batch urls.txt
```

### Eigene Config verwenden

```bash
python scraper.py scrape "URL" --config my-config.yaml
```

## ⚙️ Konfiguration

Alle Einstellungen in `config.yaml`:

### Download-Einstellungen

```yaml
download:
  output_dir: "./downloads"          # Zielverzeichnis
  create_subdirs: true               # Unterordner für jede Galerie
  max_concurrent: 5                  # Parallele Downloads
  max_retries: 3                     # Wiederholungen bei Fehler
  retry_delay: 2                     # Verzögerung zwischen Retries
```

### Scraper-Einstellungen

```yaml
scraper:
  headless: true                     # Browser unsichtbar
  browser_type: "chromium"           # chromium, firefox, webkit
  page_timeout: 30000                # Timeout in ms
  min_image_size: 50                 # Minimale Bildgröße in KB
  min_width: 500                     # Minimale Bildbreite
  min_height: 500                    # Minimale Bildhöhe
```

### Galerie-Erkennung

```yaml
detection:
  auto_detect: true                  # Automatische Erkennung
  detect_pagination: true            # Automatische Seitenerkennung
  max_pages: 100                     # Maximale Seitenanzahl

  # Custom CSS-Selektoren hinzufügen
  gallery_selectors:
    - ".gallery"
    - ".image-gallery"
    - "#gallery"
    - ".post-content"

  # Zu ignorierende Elemente
  exclude_selectors:
    - ".advertisement"
    - ".ad"
    - ".sidebar"
```

## 🎯 Wie funktioniert die intelligente Erkennung?

Der Scraper verwendet mehrere Strategien:

### 1. Container-Erkennung
- Sucht nach typischen Galerie-Containern (`.gallery`, `#gallery`, etc.)
- Analysiert DOM-Struktur für Divs mit vielen Bildern
- Findet den Container mit den meisten Bildern

### 2. Bild-Qualität-Erkennung
- Extrahiert hochauflösende Quellen (`data-src`, `data-original`, `data-full`)
- Bevorzugt große Originalbilder über Thumbnails
- Prüft `srcset` für höchste Auflösung

### 3. Größen-Filterung
- Filtert nach Dateigröße (Standard: >50 KB)
- Filtert nach Dimensionen (Standard: >500x500px)
- Ignoriert kleine UI-Elemente und Thumbnails

### 4. Element-Filterung
- Schließt Werbung, Sidebars, Navigation aus
- Ignoriert typische Nicht-Galerie-Bereiche
- Fokussiert auf Hauptinhalt

### 5. Paginierung
- Erkennt automatisch "Nächste Seite" Links
- Folgt Pagination bis zum Ende
- Sammelt Bilder von allen Seiten

## 📊 Output-Beispiel

```
╭─────────────────────────────────────────────────────╮
│ 🚀 Starting Gallery Scraper                         │
│ URL: https://example.com/gallery/12345              │
╰─────────────────────────────────────────────────────╯

📁 Output directory: ./downloads/example.com_gallery_abc123

🔍 Analyzing page structure...
✓ Found gallery container
✓ Found 45 unique images

📄 Loading page 2...
✓ Found 43 unique images

✓ Total images found: 88
✓ Pages scraped: 2

⠋ Downloading images... ━━━━━━━━━━━━━━━━━━━━━━ 88/88 • 15.2 MB • 2.3 MB/s • 0:00:00

╭─────────────── Download Summary ───────────────╮
│ Metric        │                  Value         │
├───────────────┼────────────────────────────────┤
│ ✓ Downloaded  │                     85         │
│ ⊘ Skipped     │                      2         │
│ ✗ Failed      │                      1         │
│ 📦 Total Size │                  15.23 MB      │
│ 📁 Location   │  ./downloads/example.com_...   │
╰───────────────┴────────────────────────────────╯

✨ Done!
```

## 🔧 Troubleshooting

### "No images found"
- Seite verwendet möglicherweise ungewöhnliche Struktur
- Füge custom CSS-Selektoren in `config.yaml` hinzu
- Setze `headless: false` um Browser zu sehen
- Erhöhe `js_delay` für langsam ladende Seiten

### Downloads schlagen fehl
- Erhöhe `max_retries` in der Config
- Prüfe Internetverbindung
- Manche Seiten blockieren automatisierte Zugriffe

### Zu viele/falsche Bilder
- Erhöhe `min_image_size` und `min_width`/`min_height`
- Füge weitere `exclude_selectors` hinzu
- Passe `gallery_selectors` an

## 🛠️ Erweiterte Nutzung

### Custom Headers

```yaml
advanced:
  headers:
    Referer: "https://example.com"
    Custom-Header: "value"
```

### Cookies verwenden

```yaml
advanced:
  cookies_file: "./cookies.json"
```

### Screenshots bei Fehlern

```yaml
advanced:
  screenshot_on_error: true
```

## 📝 Beispiel URLs-Datei

```text
# Galerie 1
https://example.com/gallery/1

# Galerie 2
https://example.com/album/abc

# Comic Serie
https://example.com/comic/xyz/chapter-1

# Zeilen mit # werden ignoriert
# Leere Zeilen werden übersprungen
```

## 🎨 UI-Anpassung

```yaml
ui:
  show_progress: true                # Fortschrittsbalken
  show_stats: true                   # Live-Statistiken
  theme: "auto"                      # auto, dark, light
  verbosity: "normal"                # quiet, normal, verbose
```

## 🤝 Tipps

- **Für JavaScript-heavy Seiten**: Der Scraper wartet automatisch auf Lazy-Loading
- **Für langsame Verbindungen**: Reduziere `max_concurrent` auf 2-3
- **Für spezifische Seiten**: Nutze Browser-DevTools um CSS-Selektoren zu finden
- **Batch-Downloads**: Nutze `urls.txt` für viele Galerien gleichzeitig

## ⚠️ Hinweis

Bitte respektiere die Nutzungsbedingungen der Webseiten und überlaste Server nicht mit zu vielen gleichzeitigen Anfragen.

## 📜 Lizenz

MIT License - Nutze den Code wie du möchtest!

---

**Viel Spaß beim Scrapen! 🎉**