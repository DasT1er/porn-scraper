# 🎯 Intelligent Gallery Scraper V2 - Hybrid Edition

Ein intelligenter, automatischer Scraper für Bildergalerien und Comics mit **Hybrid-Technologie**: Nutzt Requests für einfache Seiten und Selenium für JavaScript-heavy Seiten.

## ✨ Features

- 🎯 **Interaktives Terminal-UI** - Schönes Menü mit Pfeiltasten-Navigation (NEU!)
- 📁 **Auto-Kategorie-Scraper** - Scraped ganze Kategorien automatisch (NEU!)
- 📝 **Metadata-Extraktion** - Speichert Titel, Tags, Künstler, Datum automatisch (NEU!)
- 🤖 **Automatische Galerie-Erkennung** - Findet Galerien ohne manuelle Konfiguration
- ⚡ **Hybrid-Modus** - Versucht erst schnelle Methode, dann Browser wenn nötig
- 🎨 **Schönes Rich UI** - Farben, Fortschrittsbalken, Live-Statistiken
- 📄 **Multi-Page Support** - Automatisches Laden aller Seiten mit Paginierung
- 🧠 **Smart Filtering** - Ignoriert Werbung, Thumbnails und UI-Elemente
- 📦 **Batch Processing** - Mehrere Galerien aus einer Liste herunterladen
- 🔄 **Retry Logic** - Automatische Wiederholung bei Fehlern
- ⚡ **Concurrent Downloads** - Schneller paralleler Download
- 🖼️ **Image Validation** - Filtert nach Größe und Auflösung
- 🌐 **Selenium Support** - Funktioniert auf ALLEN Webseiten (auch JavaScript-heavy)

## 🚀 Installation

### Windows - Super Einfach!

```bash
# 1. Installiere alle Dependencies
pip install -r requirements.txt
```

**Das war's!** Keine Browser-Installation nötig - `webdriver-manager` macht das automatisch!

## 🎯 Quick Start - Interaktives UI (Empfohlen!)

### NEU: Schönes Terminal-Interface! ✨

```bash
python scraper_ui.py
```

**Das öffnet ein interaktives Menü mit:**

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🎯  INTELLIGENT GALLERY SCRAPER V2 - INTERACTIVE UI  🎯   ║
║                                                              ║
║              Beautiful • Fast • Intelligent                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

? What would you like to do?
  📷 Scrape Single Gallery
❯ 📁 Scrape Entire Category (Auto)
  📋 Batch Scrape from File
  ⚙️  Settings
  ❌ Exit
```

**Features:**
- ⬆️⬇️ **Pfeiltasten-Navigation** - Einfach und intuitiv
- 📁 **Kategorie-Scraper** - Gib Kategorie-URL ein → alle Galerien werden automatisch gefunden und gescraped
- 📋 **Galerie-Vorschau** - Zeigt alle gefundenen Galerien vor dem Download
- ✅ **Bestätigung** - Du siehst was gescraped wird bevor es losgeht
- 🎨 **Schöne Tabellen** - Übersichtliche Darstellung aller Galerien

### Beispiel: Ganze Kategorie scrapen

1. Starte das UI: `python scraper_ui.py`
2. Wähle "📁 Scrape Entire Category (Auto)"
3. Gib URL ein: `https://multporn.net/comics`
4. Der Scraper findet automatisch alle Galerien in der Kategorie
5. Du siehst eine Übersicht aller gefundenen Galerien
6. Bestätige mit Enter → Alle werden automatisch gescraped!

**So einfach war Scraping noch nie!** 🚀

---

## 📖 Verwendung (Command Line)

### Einzelne Galerie scrapen

```bash
# Auto-Modus (empfohlen) - probiert erst Light, dann Browser
python scraper_v2.py scrape "https://multporn.net/comics/moonstruck"

# Nur Light-Modus (schnell, nur für einfache Seiten)
python scraper_v2.py scrape "https://example.com/gallery" --mode light

# Nur Browser-Modus (langsamer, funktioniert überall)
python scraper_v2.py scrape "https://xlecx.one/comic" --mode browser
```

Mit custom Output-Verzeichnis:
```bash
python scraper_v2.py scrape "URL" --output ./my-downloads
```

### Mehrere Galerien (Batch Mode)

1. Erstelle eine Datei `urls.txt` mit URLs (eine pro Zeile):
```text
https://multporn.net/comics/moonstruck
https://allporncomic.com/porncomic/the-pastime/
https://xlecx.one/57888-masters-corruption-2.html
```

2. Führe den Batch-Scraper aus:
```bash
python scraper_v2.py batch urls.txt
```

Mit mode-Option:
```bash
python scraper_v2.py batch urls.txt --mode auto
```

## 🎯 Scraping-Modi

### Auto-Modus (Standard) ⭐
```bash
python scraper_v2.py scrape "URL" --mode auto
```
- Versucht **zuerst** Requests + BeautifulSoup (schnell!)
- Falls zu wenig Bilder gefunden → automatisch Selenium
- **Beste Wahl** für die meisten Fälle

### Light-Modus (Schnell)
```bash
python scraper_v2.py scrape "URL" --mode light
```
- Nur Requests + BeautifulSoup
- Sehr schnell, wenig RAM
- Funktioniert auf einfachen Seiten wie multporn.net, pornpics.de

### Browser-Modus (Zuverlässig)
```bash
python scraper_v2.py scrape "URL" --mode browser
```
- Nur Selenium (echter Browser)
- Funktioniert auf ALLEN Seiten
- Perfekt für xlecx.one, kingcomix, allporncomic

## 📁 Auto-Kategorie-Scraper (NEU!)

### Ganze Kategorien automatisch scrapen

Der Scraper kann jetzt automatisch **alle Galerien in einer Kategorie** finden und scrapen!

**Beispiel-Kategorien:**
```text
https://multporn.net/comics
https://multporn.net/comic/star-vs-the-forces-of-evil
https://allporncomic.com/category/xxx-comics/
https://hqporn.pics/amateurs/
```

### Wie es funktioniert:

1. **Kategorie-Erkennung**
   - Scannt die Kategorie-Seite
   - Findet automatisch alle Galerie-Links
   - Folgt Paginierung (mehrere Seiten)

2. **Smart Link-Erkennung**
   - Erkennt Galerie-URLs automatisch
   - Filtert Pagination, Filter, Navigation raus
   - Findet nur echte Galerien

3. **Vorschau & Bestätigung**
   - Zeigt alle gefundenen Galerien
   - Du bestätigst vor dem Download
   - Dann werden alle automatisch gescraped

### Via Interactive UI (Empfohlen):

```bash
python scraper_ui.py
# Wähle: "📁 Scrape Entire Category (Auto)"
# Gib Kategorie-URL ein
# Fertig! ✨
```

### Via Command Line:

Nutze das Interactive UI - es ist viel einfacher! Das CLI unterstützt momentan nur einzelne Galerien und Batch-Files.

### Beispiel-Output:

```
🔍 Scanning Category
https://multporn.net/comics

📄 Scanning page 1...
✓ Found 30 galleries on page 1
📄 Scanning page 2...
✓ Found 28 galleries on page 2

✓ Total galleries found: 58

┌─────────────── Found Galleries ───────────────┐
│ Nr.  │ Gallery URL                            │
├──────┼────────────────────────────────────────┤
│ 1    │ https://multporn.net/comics/comic1     │
│ 2    │ https://multporn.net/comics/comic2     │
│ ...  │ ... and 56 more                        │
└──────┴────────────────────────────────────────┘

? Scrape all 58 galleries? Yes

═══ Gallery 1/58 ═══
🚀 Starting Gallery Scraper...
...
```

**Super praktisch für:**
- Ganze Comic-Serien herunterladen
- Alle Galerien eines Künstlers
- Komplette Kategorien archivieren
- Neue Uploads in deinen Lieblings-Kategorien

## 📝 Metadata-Extraktion (NEU!)

### Automatische Galerie-Informationen

Der Scraper extrahiert automatisch Metadaten aus jeder Galerie und speichert sie als `metadata.json`:

**Extrahierte Felder:**
- 📌 **Titel** - Galerie-Name
- 🏷️ **Tags** - Alle Tags/Kategorien
- 👨‍🎨 **Künstler** - Author/Artist Name
- 📅 **Datum** - Upload/Veröffentlichungsdatum
- 📂 **Kategorie** - Serie/Kategorie
- 📄 **Beschreibung** - Galerie-Beschreibung
- 🔗 **URL** - Original-URL
- ⏰ **Scraped At** - Wann du es heruntergeladen hast
- 🖼️ **Anzahl Bilder** - Wie viele Bilder

### Beispiel metadata.json:

```json
{
  "url": "https://multporn.net/comics/moonstruck",
  "scraped_at": "2026-01-16T15:30:00",
  "image_count": 45,
  "title": "Moonstruck - Star vs The Forces of Evil",
  "tags": ["Star Butterfly", "Marco Diaz", "Parody", "Comedy"],
  "artist": "BlueNightKitty",
  "date": "2024-12-15",
  "category": "Star vs The Forces of Evil",
  "description": "A fun parody comic featuring Star and Marco..."
}
```

### Wozu ist das gut?

- 🔍 **Durchsuchbar** - Finde Galerien später wieder
- 📊 **Statistiken** - Wieviele Galerien von welchem Künstler?
- 🗂️ **Organisation** - Sortiere nach Tags, Datum, Künstler
- 📋 **Datenbank** - Import in eigene Datenbank möglich
- 🏷️ **Tagging** - Automatisches Tagging für Media-Player

### Konfiguration:

```yaml
# In config.yaml
metadata:
  save_metadata: true  # false um zu deaktivieren
```

**Hinweis:** Metadata wird intelligent extrahiert - der Scraper versucht mehrere Methoden um die Informationen zu finden!

## ⚙️ Konfiguration

Alle Einstellungen in `config.yaml`:

### Hybrid-Mode Einstellungen

```yaml
scraper:
  # Standard-Modus
  default_mode: "auto"  # auto, light, browser

  # Minimum Bilder für Light-Mode Erfolg
  # Wenn weniger gefunden → wechselt zu Browser
  min_images_threshold: 5

  # Browser unsichtbar laufen lassen
  headless: true

  # Wartezeit für Seiten-Load (Sekunden)
  page_load_wait: 3
```

### Download-Einstellungen

```yaml
download:
  output_dir: "./downloads"          # Zielverzeichnis
  create_subdirs: true               # Unterordner für jede Galerie
  max_concurrent: 5                  # Parallele Downloads
  max_retries: 3                     # Wiederholungen bei Fehler
  retry_delay: 2                     # Verzögerung zwischen Retries
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

## 🎯 Wie funktioniert der Hybrid-Modus?

### Auto-Modus Flow:

1. **Light-Versuch** (Requests + BeautifulSoup)
   - Schneller HTTP GET Request
   - Parst HTML direkt
   - Sucht Galerie-Container und Bilder

2. **Erfolgs-Check**
   - Hat Light-Mode ≥ 5 Bilder gefunden?
   - ✅ Ja → Fertig! (schnell & effizient)
   - ❌ Nein → Weiter zu Schritt 3

3. **Browser-Versuch** (Selenium)
   - Startet echten Chrome Browser
   - Führt JavaScript aus
   - Wartet auf Lazy-Loading
   - Scrollt für alle Bilder

### Beispiel-Output:

```
╭─────────────────────────────────────────────────────╮
│ 🚀 Starting Gallery Scraper                         │
│ URL: https://multporn.net/comics/moonstruck         │
│ Mode: auto                                          │
╰─────────────────────────────────────────────────────╯

📁 Output directory: ./downloads/multporn.net_comics_...

⚡ Trying Light Mode (Requests + BeautifulSoup)...
🔍 Analyzing page structure...
✓ Found gallery container
✓ Found 45 images on page 1
✓ Light mode successful! Found 45 images

⠋ Downloading images... ━━━━━━━━━━━━━━━━━━━━━━ 45/45 • 8.2 MB • 2.1 MB/s • 0:00:00

╭─────────────── Download Summary ───────────────╮
│ Metric        │                  Value         │
├───────────────┼────────────────────────────────┤
│ ✓ Downloaded  │                     45         │
│ ⊘ Skipped     │                      0         │
│ ✗ Failed      │                      0         │
│ 📦 Total Size │                   8.23 MB      │
│ 📁 Location   │  ./downloads/multporn.net_...  │
╰───────────────┴────────────────────────────────╯

✨ Done!
```

## 🌐 Welche Seiten funktionieren?

### ✅ Light-Mode (Requests) funktioniert:
- multporn.net ⚡
- pornpics.de ⚡
- lamalinks.com ⚡
- hqporn.pics ⚡
- Die meisten älteren Galerie-Seiten

### 🌐 Browser-Mode (Selenium) nötig:
- xlecx.one (Lazy Loading)
- kingcomix.com (JavaScript Reader)
- allporncomic.com (Comic Reader)
- x3vid.com (Dynamischer Content)
- Moderne JavaScript-heavy Seiten

### ⚡ Auto-Mode macht es automatisch!
Der Scraper entscheidet selbst was nötig ist.

## 🔧 Troubleshooting

### Selenium startet nicht

Der `webdriver-manager` lädt beim ersten Mal Chrome-Driver automatisch herunter. Wenn das fehlschlägt:

```bash
# Chrome manuell aktualisieren
# Dann nochmal probieren
python scraper_v2.py scrape "URL" --mode browser
```

### "Too few images found"

Falls Auto-Mode zu früh zu Browser wechselt, ändere den Threshold:

```yaml
# In config.yaml
scraper:
  min_images_threshold: 3  # Standard: 5
```

### Light-Mode findet nichts

Manche Seiten haben ungewöhnliche Strukturen. Füge custom Selektoren hinzu:

```yaml
detection:
  gallery_selectors:
    - ".gallery"
    - ".your-custom-selector"  # Von Browser DevTools
```

Oder nutze direkt Browser-Mode:
```bash
python scraper_v2.py scrape "URL" --mode browser
```

### Zu viele/falsche Bilder
- Erhöhe `min_image_size` und `min_width`/`min_height`
- Füge weitere `exclude_selectors` hinzu

## 💡 Tipps

### Für maximale Geschwindigkeit:
```bash
# Nutze Light-Mode wenn du weißt dass die Seite einfach ist
python scraper_v2.py scrape "URL" --mode light
```

### Für maximale Zuverlässigkeit:
```bash
# Nutze Browser-Mode direkt
python scraper_v2.py scrape "URL" --mode browser
```

### Für beste Balance:
```bash
# Auto-Mode (Standard)
python scraper_v2.py scrape "URL"
```

### Batch-Processing optimieren:
```yaml
# In config.yaml
download:
  max_concurrent: 3  # Reduziere bei langsamer Verbindung
```

## 📊 Performance-Vergleich

| Modus | Geschwindigkeit | Kompatibilität | RAM | Empfohlen für |
|-------|----------------|----------------|-----|---------------|
| **Light** | ⚡⚡⚡⚡⚡ Sehr schnell | ~60% der Seiten | 50 MB | multporn, pornpics, etc. |
| **Browser** | ⚡⚡ Langsamer | 100% aller Seiten | 200 MB | xlecx, kingcomix, etc. |
| **Auto** | ⚡⚡⚡⚡ Schnell | 100% aller Seiten | 50-200 MB | **Alles!** |

## 📝 Beispiel URLs

```text
# Einfache Seiten (Light-Mode funktioniert)
https://multporn.net/comics/moonstruck
https://www.pornpics.de/galleries/met-art-x/

# JavaScript-heavy (Browser-Mode nötig)
https://xlecx.one/57888-masters-corruption-2.html
https://kingcomix.com/princess-treatment-kinkymation/
https://allporncomic.com/porncomic/the-pastime/

# Auto-Mode funktioniert auf ALLEN!
```

## 🆚 Scraper V1 vs V2

| Feature | V1 (Playwright) | V2 (Hybrid) |
|---------|----------------|-------------|
| Installation | ❌ Kompliziert | ✅ Einfach |
| Windows Support | ❌ PATH Probleme | ✅ Funktioniert |
| Geschwindigkeit | ⚡⚡ Mittel | ⚡⚡⚡⚡ Schnell |
| Kompatibilität | ✅ 100% | ✅ 100% |
| RAM Verbrauch | 200 MB | 50-200 MB |
| Intelligenz | ✅ Smart | ✅✅ Sehr Smart |

## 🎁 Bonus-Features

### Dry-Run Mode (zukünftig)
```bash
# Nur zeigen was gefunden wird, nicht downloaden
python scraper_v2.py scrape "URL" --dry-run
```

### Verbose Mode
```bash
# Mehr Debug-Info
python scraper_v2.py scrape "URL" --verbose
```

## ⚠️ Hinweis

Bitte respektiere die Nutzungsbedingungen der Webseiten und überlaste Server nicht mit zu vielen gleichzeitigen Anfragen.

## 📜 Lizenz

MIT License - Nutze den Code wie du möchtest!

---

**Viel Spaß beim Scrapen mit dem Hybrid-Scraper! 🎉**

Made with ❤️ for efficient gallery scraping
