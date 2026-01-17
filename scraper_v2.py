#!/usr/bin/env python3
"""
Intelligent Adult Content Gallery Scraper - Hybrid Version
Automatically detects and downloads image galleries and comics
Uses Requests for simple pages, Selenium for JavaScript-heavy pages
"""

import asyncio
import re
import time
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple
from urllib.parse import urljoin, urlparse
import hashlib

# Web scraping
import requests
from bs4 import BeautifulSoup

# Try to import Playwright (preferred)
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# Fallback to Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

# Import undetected-chromedriver as fallback
try:
    import undetected_chromedriver as uc
    HAS_UC = True
except ImportError:
    HAS_UC = False
    # Fallback to regular selenium with webdriver-manager
    try:
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        pass

# HTTP and async
import httpx

# UI
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)
from rich.panel import Panel
from rich.table import Table
from rich import box
import yaml
import click
import io

# Optional Pillow import for image validation
try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


console = Console()


class MetadataExtractor:
    """Extracts metadata from gallery pages"""

    def __init__(self, config: dict):
        self.config = config
        self.metadata_config = config.get('metadata', {})

    def extract_metadata(self, html: str, url: str, image_count: int) -> Dict:
        """
        Extract metadata from gallery HTML

        Args:
            html: Page HTML
            url: Gallery URL
            image_count: Number of images found

        Returns:
            Dictionary with metadata
        """
        soup = BeautifulSoup(html, 'html.parser')

        metadata = {
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'image_count': image_count,
        }

        # Extract title
        metadata['title'] = self._extract_title(soup, url)

        # Extract tags
        metadata['tags'] = self._extract_tags(soup)

        # Extract artist/author
        metadata['artist'] = self._extract_artist(soup)

        # Extract date
        metadata['date'] = self._extract_date(soup)

        # Extract category/series
        metadata['category'] = self._extract_category(soup, url)

        # Extract description
        metadata['description'] = self._extract_description(soup)

        return metadata

    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """Extract gallery title"""
        # Try multiple methods
        title_selectors = [
            'h1',
            '.title',
            '.post-title',
            '#title',
            'title',
            '.entry-title',
            '.comic-title',
            '.gallery-title',
        ]

        for selector in title_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    title = element.get_text().strip()
                    if title and len(title) > 3:
                        # Clean up title
                        title = re.sub(r'\s+', ' ', title)
                        return title
            except:
                continue

        # Fallback: use URL
        return self._title_from_url(url)

    def _title_from_url(self, url: str) -> str:
        """Generate title from URL"""
        path = urlparse(url).path
        # Get last part of path
        parts = [p for p in path.split('/') if p]
        if parts:
            title = parts[-1]
            # Replace dashes/underscores with spaces
            title = title.replace('-', ' ').replace('_', ' ')
            # Remove file extensions
            title = re.sub(r'\.(html|php|aspx?)$', '', title)
            # Capitalize
            title = title.title()
            return title
        return "Unknown Gallery"

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract tags from page"""
        tags = []

        # Common tag selectors
        tag_selectors = [
            '.tags a',
            '.tag',
            '.post-tag',
            'a[rel="tag"]',
            '.label',
            '.badge',
        ]

        for selector in tag_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    tag = elem.get_text().strip()
                    if tag and len(tag) > 1 and tag not in tags:
                        tags.append(tag)
            except:
                continue

        return tags[:20]  # Limit to 20 tags

    def _extract_artist(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract artist/author name"""
        artist_selectors = [
            '.artist',
            '.author',
            '.by-author a',
            'a[rel="author"]',
            '.creator',
            '.artist-name',
        ]

        for selector in artist_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    artist = element.get_text().strip()
                    if artist and len(artist) > 2:
                        return artist
            except:
                continue

        return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract upload/publish date"""
        date_selectors = [
            'time',
            '.date',
            '.published',
            '.post-date',
            '.upload-date',
        ]

        for selector in date_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    # Try datetime attribute
                    date_str = element.get('datetime')
                    if date_str:
                        return date_str

                    # Try text content
                    date_text = element.get_text().strip()
                    if date_text:
                        return date_text
            except:
                continue

        return None

    def _extract_category(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """Extract category or series"""
        category_selectors = [
            '.category',
            '.series',
            '.breadcrumb a',
            '.cat-links a',
        ]

        for selector in category_selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    # Return last category (most specific)
                    cat = elements[-1].get_text().strip()
                    if cat and len(cat) > 2:
                        return cat
            except:
                continue

        # Try from URL path
        path = urlparse(url).path
        if '/category/' in path:
            parts = path.split('/category/')
            if len(parts) > 1:
                return parts[1].split('/')[0].replace('-', ' ').title()

        return None

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract gallery description"""
        desc_selectors = [
            '.description',
            '.content',
            '.post-content',
            '.entry-content',
            'meta[name="description"]',
        ]

        for selector in desc_selectors:
            try:
                if selector.startswith('meta'):
                    element = soup.select_one(selector)
                    if element:
                        desc = element.get('content', '').strip()
                        if desc and len(desc) > 10:
                            return desc[:500]  # Limit length
                else:
                    element = soup.select_one(selector)
                    if element:
                        desc = element.get_text().strip()
                        if desc and len(desc) > 10:
                            # Limit and clean
                            desc = re.sub(r'\s+', ' ', desc)
                            return desc[:500]
            except:
                continue

        return None

    def save_metadata(self, metadata: Dict, output_dir: Path):
        """Save metadata to JSON file"""
        if not self.metadata_config.get('save_metadata', True):
            return

        metadata_file = output_dir / 'metadata.json'

        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            console.print(f"[green]✓ Saved metadata to {metadata_file.name}[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ Failed to save metadata: {e}[/yellow]")


class GalleryDetector:
    """Smart gallery detection using DOM analysis"""

    def __init__(self, config: dict):
        self.config = config
        self.detection_config = config.get('detection', {})

    def detect_gallery_images_html(self, html: str, base_url: str) -> List[str]:
        """Detect all gallery images from HTML (works with both Requests and Selenium)"""
        soup = BeautifulSoup(html, 'html.parser')

        # Method 1: Try to find gallery container
        gallery_container = self._find_gallery_container(soup)

        if gallery_container:
            console.print(f"[green]✓ Found gallery container[/green]")
            images = self._extract_images_from_container(gallery_container, base_url)
        else:
            # Method 2: Find all large images on the page
            console.print(f"[yellow]⚠ No gallery container found, analyzing all images...[/yellow]")
            images = self._find_all_images(soup, base_url)

        # Remove duplicates while preserving order
        unique_images = list(dict.fromkeys(images))

        return unique_images

    def _find_gallery_container(self, soup: BeautifulSoup) -> Optional[any]:
        """Find the main gallery container using heuristics"""
        selectors = self.detection_config.get('gallery_selectors', [])
        exclude_selectors = self.detection_config.get('exclude_selectors', [])

        # Try each selector
        for selector in selectors:
            try:
                containers = soup.select(selector)
                if containers:
                    # Return the container with most images
                    best_container = max(
                        containers,
                        key=lambda c: len(c.find_all('img')),
                        default=None
                    )
                    if best_container and len(best_container.find_all('img')) > 0:
                        return best_container
            except Exception:
                continue

        # Fallback: Find div/article with most images
        all_containers = soup.find_all(['div', 'article', 'section', 'main'])

        candidates = []
        for container in all_containers:
            # Skip excluded containers
            if any(container.select(ex_sel) for ex_sel in exclude_selectors if ex_sel):
                continue

            img_count = len(container.find_all('img'))
            if img_count >= 3:  # Minimum 3 images to be considered a gallery
                candidates.append((container, img_count))

        if candidates:
            # Return container with most images
            return max(candidates, key=lambda x: x[1])[0]

        return None

    def _extract_images_from_container(self, container, base_url: str) -> List[str]:
        """Extract all image URLs from a container"""
        images = []

        # Find all img tags
        for img in container.find_all('img'):
            img_url = self._get_best_image_url(img, base_url)
            if img_url:
                images.append(img_url)

        # Also check for links to images
        for link in container.find_all('a'):
            href = link.get('href', '')
            if self._is_image_url(href):
                images.append(urljoin(base_url, href))

        return images

    def _find_all_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find all images on the page"""
        images = []

        for img in soup.find_all('img'):
            img_url = self._get_best_image_url(img, base_url)
            if img_url:
                images.append(img_url)

        # Check links to images
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if self._is_image_url(href):
                images.append(urljoin(base_url, href))

        return images

    def _get_best_image_url(self, img_tag, base_url: str) -> Optional[str]:
        """Get the highest quality image URL from an img tag"""
        # Priority: data-src, data-original, src
        candidates = [
            img_tag.get('data-src'),
            img_tag.get('data-original'),
            img_tag.get('data-full'),
            img_tag.get('data-large'),
            img_tag.get('data-lazy'),
            self._parse_srcset(img_tag),
            img_tag.get('src'),
        ]

        for url in candidates:
            if url and self._is_image_url(url) and not url.startswith('data:'):
                return urljoin(base_url, url)

        return None

    def _parse_srcset(self, img_tag) -> Optional[str]:
        """Safely parse srcset attribute"""
        try:
            srcset = img_tag.get('srcset', '') if img_tag else None
            if not srcset:
                return None

            # srcset format: "url1 width1, url2 width2"
            # Get first URL
            parts = srcset.split(',')[0].split()
            return parts[0] if parts else None
        except (AttributeError, IndexError, TypeError):
            return None

    @staticmethod
    def _is_image_url(url: str) -> bool:
        """Check if URL is likely an image"""
        if not url or url.startswith('data:'):
            return False

        # Remove query parameters for extension check
        url_path = urlparse(url).path.lower()
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
        return url_path.endswith(image_extensions)

    def detect_next_page(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """Detect next page URL for pagination"""
        if not self.detection_config.get('detect_pagination', True):
            return None

        selectors = self.detection_config.get('pagination_selectors', [])

        for selector in selectors:
            try:
                next_links = soup.select(selector)
                for link in next_links:
                    href = link.get('href')
                    if href:
                        return urljoin(current_url, href)
            except Exception:
                continue

        return None


class ImageDownloader:
    """Handles image downloading with progress tracking"""

    def __init__(self, config: dict):
        self.config = config
        self.download_config = config.get('download', {})
        self.min_size = config['scraper'].get('min_image_size', 50) * 1024  # KB to bytes
        self.min_width = config['scraper'].get('min_width', 500)
        self.min_height = config['scraper'].get('min_height', 500)

        # Show warning if Pillow is not available
        if not HAS_PILLOW:
            console.print("[yellow]⚠ Pillow not installed - image dimension validation disabled[/yellow]")
            console.print("[yellow]  Only file size will be checked. Install Pillow for full validation:[/yellow]")
            console.print("[yellow]  pip install Pillow --prefer-binary[/yellow]\n")

    async def download_images(
        self,
        image_urls: List[str],
        output_dir: Path,
        progress: Progress,
        task_id: int
    ) -> Dict[str, int]:
        """Download all images with progress tracking"""

        stats = {
            'downloaded': 0,
            'skipped': 0,
            'failed': 0,
            'total_bytes': 0
        }

        # Update total
        progress.update(task_id, total=len(image_urls))

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            semaphore = asyncio.Semaphore(self.download_config.get('max_concurrent', 5))

            tasks = [
                self._download_single_image(
                    client, url, output_dir, index, semaphore, progress, task_id, stats
                )
                for index, url in enumerate(image_urls, 1)
            ]

            await asyncio.gather(*tasks, return_exceptions=True)

        return stats

    async def _download_single_image(
        self,
        client: httpx.AsyncClient,
        url: str,
        output_dir: Path,
        index: int,
        semaphore: asyncio.Semaphore,
        progress: Progress,
        task_id: int,
        stats: dict
    ):
        """Download a single image with retry logic"""
        async with semaphore:
            max_retries = self.download_config.get('max_retries', 3)
            retry_delay = self.download_config.get('retry_delay', 2)

            for attempt in range(max_retries):
                try:
                    # Download image
                    response = await client.get(url)
                    response.raise_for_status()

                    content = response.content

                    # Validate image
                    if not self._validate_image(content):
                        stats['skipped'] += 1
                        progress.update(task_id, advance=1)
                        return

                    # Generate filename
                    filename = self._generate_filename(url, index)
                    filepath = output_dir / filename

                    # Save image
                    filepath.write_bytes(content)

                    stats['downloaded'] += 1
                    stats['total_bytes'] += len(content)
                    progress.update(task_id, advance=1)

                    return

                except Exception as e:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                    else:
                        console.print(f"[red]✗ Failed to download {url}: {e}[/red]")
                        stats['failed'] += 1
                        progress.update(task_id, advance=1)

    def _validate_image(self, content: bytes) -> bool:
        """Validate image size and dimensions"""
        # Check file size
        if len(content) < self.min_size:
            return False

        # Check dimensions (only if Pillow is available)
        if HAS_PILLOW:
            try:
                img = Image.open(io.BytesIO(content))
                width, height = img.size

                if width < self.min_width or height < self.min_height:
                    return False

                return True
            except Exception:
                return False
        else:
            # Without Pillow, we can only validate file size
            # Assume image is valid if it's large enough
            return True

    def _generate_filename(self, url: str, index: int) -> str:
        """Generate filename from URL and index"""
        # Extract original filename
        path = urlparse(url).path
        original_name = Path(path).name

        # Get extension
        ext = Path(original_name).suffix or '.jpg'

        # Use pattern from config
        pattern = self.download_config.get('file_pattern', '{index:03d}_{filename}')

        filename = pattern.format(
            index=index,
            filename=Path(original_name).stem
        )

        return f"{filename}{ext}"


class HybridScraper:
    """Hybrid scraper that tries Requests first, falls back to Selenium"""

    def __init__(self, config_path: str = 'config.yaml'):
        self.config = self._load_config(config_path)
        self.detector = GalleryDetector(self.config)
        self.downloader = ImageDownloader(self.config)
        self.metadata_extractor = MetadataExtractor(self.config)
        self.driver = None

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _create_selenium_driver(self):
        """Create a Selenium Chrome driver with undetected-chromedriver"""
        console.print("[cyan]🌐 Starting browser (Selenium)...[/cyan]")

        headless = self.config['scraper'].get('headless', True)
        user_agent = self.config['scraper'].get('user_agent')

        # Try undetected-chromedriver first (best anti-detection)
        if HAS_UC:
            try:
                console.print("[dim]Using undetected-chromedriver (better anti-detection)...[/dim]")

                options = uc.ChromeOptions()

                # Basic options
                if headless:
                    options.add_argument('--headless=new')  # New headless mode

                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--window-size=1920,1080')

                if user_agent:
                    options.add_argument(f'user-agent={user_agent}')

                # Create driver with undetected-chromedriver
                driver = uc.Chrome(options=options, use_subprocess=True)

                console.print("[green]✓ Browser ready (undetected mode)[/green]")
                return driver

            except Exception as e:
                console.print(f"[yellow]⚠ undetected-chromedriver failed: {e}[/yellow]")
                console.print(f"[yellow]Falling back to regular Selenium...[/yellow]")
        else:
            console.print("[dim]undetected-chromedriver not installed, using regular Selenium[/dim]")

        # Fallback to regular Selenium
        try:
            console.print("[dim]Initializing regular ChromeDriver...[/dim]")

            chrome_options = Options()

            if headless:
                chrome_options.add_argument('--headless=new')

            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            if user_agent:
                chrome_options.add_argument(f'user-agent={user_agent}')

            # Try to create driver
            try:
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception:
                # Last resort: try without webdriver-manager
                driver = webdriver.Chrome(options=chrome_options)

            # Hide webdriver property
            try:
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except:
                pass

            console.print("[green]✓ Browser ready (regular mode)[/green]")
            return driver

        except Exception as e:
            console.print(f"[red]✗ Failed to initialize ChromeDriver: {e}[/red]")
            console.print(f"[yellow]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/yellow]")
            console.print(f"[yellow]💡 ChromeDriver setup failed. Solutions:[/yellow]")
            console.print(f"[yellow]   1. Install undetected-chromedriver:[/yellow]")
            console.print(f"[yellow]      pip install undetected-chromedriver[/yellow]")
            console.print(f"[yellow]   2. Make sure Google Chrome is installed[/yellow]")
            console.print(f"[yellow]   3. Try sites that work with Light mode:[/yellow]")
            console.print(f"[yellow]      - multporn.net (works perfectly!)[/yellow]")
            console.print(f"[yellow]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/yellow]")
            raise

    async def scrape_gallery(self, url: str, output_dir: Optional[Path] = None, mode: str = 'auto'):
        """
        Scrape a single gallery

        Args:
            url: Gallery URL
            output_dir: Output directory
            mode: 'auto' (try requests first), 'light' (requests only), 'browser' (selenium only)
        """
        console.print(Panel.fit(
            f"[bold cyan]🚀 Starting Gallery Scraper[/bold cyan]\n[white]URL: {url}[/white]\n[yellow]Mode: {mode}[/yellow]",
            border_style="cyan"
        ))

        if output_dir is None:
            output_dir = Path(self.config['download']['output_dir'])

        # Create output directory
        if self.config['download'].get('create_subdirs', True):
            # Generate unique folder name from URL
            folder_name = self._generate_folder_name(url)
            output_dir = output_dir / folder_name

        output_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"[green]📁 Output directory: {output_dir}[/green]\n")

        all_images = []

        # Try light mode first (if auto or light)
        if mode in ['auto', 'light']:
            console.print("[cyan]⚡ Trying Light Mode (Requests + BeautifulSoup)...[/cyan]")
            all_images = await self._scrape_with_requests(url)

            min_images = self.config['scraper'].get('min_images_threshold', 5)

            if len(all_images) >= min_images:
                console.print(f"[green]✓ Light mode successful! Found {len(all_images)} images[/green]")
            elif mode == 'light':
                console.print(f"[yellow]⚠ Light mode found only {len(all_images)} images (minimum: {min_images})[/yellow]")
            else:
                console.print(f"[yellow]⚠ Light mode insufficient ({len(all_images)} images), switching to Browser mode...[/yellow]")
                all_images = []

        # Use browser mode if needed
        if (mode == 'browser') or (mode == 'auto' and len(all_images) < self.config['scraper'].get('min_images_threshold', 5)):
            if mode != 'browser':
                console.print("[cyan]🌐 Switching to Browser Mode...[/cyan]")
            else:
                console.print("[cyan]🌐 Using Browser Mode...[/cyan]")

            # Try Playwright first (better), fallback to Selenium
            if HAS_PLAYWRIGHT:
                console.print("[dim]Using Playwright (modern browser automation)[/dim]")
                all_images = await self._scrape_with_playwright(url)
            elif HAS_SELENIUM or HAS_UC:
                console.print("[dim]Using Selenium (Playwright not installed)[/dim]")
                all_images = await self._scrape_with_selenium(url)
            else:
                console.print("[red]✗ No browser automation available![/red]")
                console.print("[yellow]Install: pip install playwright && playwright install chromium[/yellow]")
                return

        if not all_images:
            console.print("[yellow]⚠ No images found![/yellow]")
            return

        console.print(f"\n[bold green]✓ Total unique images found: {len(all_images)}[/bold green]\n")

        # Download images
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            DownloadColumn(),
            TextColumn("•"),
            TransferSpeedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                "[cyan]Downloading images...",
                total=len(all_images)
            )

            stats = await self.downloader.download_images(
                all_images,
                output_dir,
                progress,
                task
            )

        # Extract and save metadata
        if self.config.get('metadata', {}).get('save_metadata', True):
            console.print("\n[cyan]📝 Extracting metadata...[/cyan]")
            try:
                # Fetch page for metadata
                headers = {
                    'User-Agent': self.config['scraper'].get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                }
                response = requests.get(url, headers=headers, timeout=30)
                metadata = self.metadata_extractor.extract_metadata(
                    response.text,
                    url,
                    len(all_images)
                )
                self.metadata_extractor.save_metadata(metadata, output_dir)
            except Exception as e:
                console.print(f"[yellow]⚠ Failed to extract metadata: {e}[/yellow]")

        # Show summary
        self._show_summary(stats, output_dir)

    async def _scrape_with_requests(self, url: str) -> List[str]:
        """Scrape using Requests + BeautifulSoup (fast, no JS)"""
        all_images = []
        visited_urls = set()
        current_url = url
        page_num = 1
        max_pages = self.config['detection'].get('max_pages', 100)

        headers = {
            'User-Agent': self.config['scraper'].get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        }

        while current_url and page_num <= max_pages:
            if current_url in visited_urls:
                break

            visited_urls.add(current_url)

            try:
                if page_num > 1:
                    console.print(f"[cyan]📄 Loading page {page_num}...[/cyan]")

                # Fetch page
                response = requests.get(current_url, headers=headers, timeout=30)
                response.raise_for_status()

                # Parse HTML
                console.print(f"[cyan]🔍 Analyzing page structure...[/cyan]")
                images = self.detector.detect_gallery_images_html(response.text, current_url)

                console.print(f"[green]✓ Found {len(images)} images on page {page_num}[/green]")
                all_images.extend(images)

                # Check for next page
                if self.config['detection'].get('detect_pagination', True):
                    soup = BeautifulSoup(response.text, 'html.parser')
                    next_url = self.detector.detect_next_page(soup, current_url)

                    if next_url and next_url != current_url:
                        current_url = next_url
                        page_num += 1
                    else:
                        break
                else:
                    break

            except Exception as e:
                console.print(f"[red]✗ Error on page {page_num}: {e}[/red]")
                break

        # Remove duplicates
        unique_images = list(dict.fromkeys(all_images))
        return unique_images

    async def _scrape_with_playwright(self, url: str) -> List[str]:
        """Scrape using Playwright (modern, better anti-detection)"""
        if not HAS_PLAYWRIGHT:
            console.print("[yellow]⚠ Playwright not installed, falling back to Selenium[/yellow]")
            return await self._scrape_with_selenium(url)

        all_images = []

        try:
            with sync_playwright() as p:
                # Launch browser
                browser = p.chromium.launch(
                    headless=self.config['scraper'].get('headless', True),
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )

                # Create context with realistic settings
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=self.config['scraper'].get('user_agent',
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                )

                page = context.new_page()

                # Navigate to page
                console.print(f"[cyan]Loading page...[/cyan]")
                page.goto(url, wait_until='networkidle', timeout=30000)

                # Wait for page to load
                page.wait_for_timeout(self.config['scraper'].get('page_load_wait', 3) * 1000)

                # Scroll to load lazy images
                console.print(f"[cyan]Scrolling to load images...[/cyan]")
                page.evaluate("""
                    () => {
                        return new Promise((resolve) => {
                            let totalHeight = 0;
                            const distance = 100;
                            const timer = setInterval(() => {
                                const scrollHeight = document.body.scrollHeight;
                                window.scrollBy(0, distance);
                                totalHeight += distance;
                                if (totalHeight >= scrollHeight) {
                                    clearInterval(timer);
                                    resolve();
                                }
                            }, 100);
                        });
                    }
                """)

                # Get page HTML
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Use detector to find images
                detector = GalleryDetector()
                all_images = detector.detect_gallery_images(soup, url)

                console.print(f"[green]✓ Found {len(all_images)} images on page 1[/green]")

                # Check for pagination
                page_num = 2
                max_pages = self.config['detection'].get('max_pages', 100)

                while page_num <= max_pages:
                    next_url = detector.detect_next_page(soup, url)

                    if not next_url or next_url == url:
                        break

                    console.print(f"[cyan]Loading page {page_num}...[/cyan]")
                    page.goto(next_url, wait_until='networkidle', timeout=30000)
                    page.wait_for_timeout(2000)

                    # Scroll again
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1000)

                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')

                    page_images = detector.detect_gallery_images(soup, next_url)
                    console.print(f"[green]✓ Found {len(page_images)} images on page {page_num}[/green]")

                    all_images.extend(page_images)
                    url = next_url
                    page_num += 1

                browser.close()

        except Exception as e:
            console.print(f"[red]✗ Playwright error: {e}[/red]")
            console.print(f"[yellow]Falling back to Selenium...[/yellow]")
            return await self._scrape_with_selenium(url)

        # Remove duplicates
        unique_images = list(dict.fromkeys(all_images))
        return unique_images

    async def _scrape_with_selenium(self, url: str) -> List[str]:
        """Scrape using Selenium (slower, supports JS)"""
        all_images = []

        try:
            self.driver = self._create_selenium_driver()

            visited_urls = set()
            current_url = url
            page_num = 1
            max_pages = self.config['detection'].get('max_pages', 100)

            while current_url and page_num <= max_pages:
                if current_url in visited_urls:
                    break

                visited_urls.add(current_url)

                if page_num > 1:
                    console.print(f"[cyan]📄 Loading page {page_num}...[/cyan]")

                # Load page
                self.driver.get(current_url)

                # Wait for images to load
                wait_time = self.config['scraper'].get('page_load_wait', 3)
                time.sleep(wait_time)

                # Scroll to load lazy images
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)

                # Get page source
                console.print(f"[cyan]🔍 Analyzing page structure...[/cyan]")
                page_source = self.driver.page_source
                images = self.detector.detect_gallery_images_html(page_source, current_url)

                console.print(f"[green]✓ Found {len(images)} images on page {page_num}[/green]")
                all_images.extend(images)

                # Check for next page
                if self.config['detection'].get('detect_pagination', True):
                    soup = BeautifulSoup(page_source, 'html.parser')
                    next_url = self.detector.detect_next_page(soup, current_url)

                    if next_url and next_url != current_url:
                        current_url = next_url
                        page_num += 1
                    else:
                        break
                else:
                    break

        finally:
            if self.driver:
                self.driver.quit()

        # Remove duplicates
        unique_images = list(dict.fromkeys(all_images))
        return unique_images

    def _generate_folder_name(self, url: str) -> str:
        """Generate folder name from URL"""
        # Use URL hash for unique folder name
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]

        # Extract domain
        domain = urlparse(url).netloc.replace('www.', '')

        # Clean path
        path = urlparse(url).path.strip('/').replace('/', '_')
        if len(path) > 50:
            path = path[:50]

        if path:
            return f"{domain}_{path}_{url_hash}"
        else:
            return f"{domain}_{url_hash}"

    def _show_summary(self, stats: dict, output_dir: Path):
        """Show download summary"""
        table = Table(title="Download Summary", box=box.ROUNDED, border_style="green")

        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")

        table.add_row("✓ Downloaded", str(stats['downloaded']))
        table.add_row("⊘ Skipped", str(stats['skipped']))
        table.add_row("✗ Failed", str(stats['failed']))
        table.add_row("📦 Total Size", f"{stats['total_bytes'] / 1024 / 1024:.2f} MB")
        table.add_row("📁 Location", str(output_dir))

        console.print("\n")
        console.print(table)
        console.print("\n[bold green]✨ Done![/bold green]\n")

    async def scrape_multiple(self, urls: List[str], mode: str = 'auto'):
        """Scrape multiple galleries from a list of URLs"""
        console.print(Panel.fit(
            f"[bold cyan]🚀 Batch Scraper[/bold cyan]\n[white]Total galleries: {len(urls)}[/white]\n[yellow]Mode: {mode}[/yellow]",
            border_style="cyan"
        ))

        for i, url in enumerate(urls, 1):
            console.print(f"\n[bold cyan]═══ Gallery {i}/{len(urls)} ═══[/bold cyan]\n")
            try:
                await self.scrape_gallery(url, mode=mode)
            except Exception as e:
                console.print(f"[red]✗ Error scraping {url}: {e}[/red]")
                continue

        console.print(f"\n[bold green]✨ All galleries processed![/bold green]\n")


@click.group()
def cli():
    """Intelligent Adult Content Gallery Scraper - Hybrid Version"""
    pass


@cli.command()
@click.argument('url')
@click.option('--output', '-o', help='Output directory', type=click.Path())
@click.option('--config', '-c', default='config.yaml', help='Config file path')
@click.option('--mode', '-m', type=click.Choice(['auto', 'light', 'browser']), default='auto',
              help='Scraping mode: auto (try light first), light (requests only), browser (selenium only)')
def scrape(url: str, output: Optional[str], config: str, mode: str):
    """Scrape a single gallery from URL"""
    scraper = HybridScraper(config)
    output_dir = Path(output) if output else None
    asyncio.run(scraper.scrape_gallery(url, output_dir, mode))


@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--config', '-c', default='config.yaml', help='Config file path')
@click.option('--mode', '-m', type=click.Choice(['auto', 'light', 'browser']), default='auto',
              help='Scraping mode: auto (try light first), light (requests only), browser (selenium only)')
def batch(file: str, config: str, mode: str):
    """Scrape multiple galleries from a file (one URL per line)"""
    with open(file, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    scraper = HybridScraper(config)
    asyncio.run(scraper.scrape_multiple(urls, mode))


if __name__ == '__main__':
    cli()
