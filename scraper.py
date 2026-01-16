#!/usr/bin/env python3
"""
Intelligent Adult Content Gallery Scraper
Automatically detects and downloads image galleries and comics
"""

import asyncio
import re
from pathlib import Path
from typing import List, Optional, Dict, Set
from urllib.parse import urljoin, urlparse
import hashlib

from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup
import httpx
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
from rich.live import Live
from rich import box
import yaml
import click
from PIL import Image
import io


console = Console()


class GalleryDetector:
    """Smart gallery detection using DOM analysis"""

    def __init__(self, config: dict):
        self.config = config
        self.detection_config = config.get('detection', {})

    async def detect_gallery_images(self, page: Page, url: str) -> List[str]:
        """Detect all gallery images on the page"""
        console.print(f"[cyan]🔍 Analyzing page structure...[/cyan]")

        # Wait for images to load
        if self.config['scraper'].get('wait_for_images', True):
            await page.wait_for_load_state('networkidle', timeout=30000)
            await asyncio.sleep(1)  # Extra wait for lazy-loaded images

        # Get page content
        content = await page.content()
        soup = BeautifulSoup(content, 'lxml')

        # Method 1: Try to find gallery container
        gallery_container = self._find_gallery_container(soup)

        if gallery_container:
            console.print(f"[green]✓ Found gallery container[/green]")
            images = self._extract_images_from_container(gallery_container, url)
        else:
            # Method 2: Find all large images on the page
            console.print(f"[yellow]⚠ No gallery container found, analyzing all images...[/yellow]")
            images = await self._find_large_images(page, url)

        # Remove duplicates while preserving order
        unique_images = list(dict.fromkeys(images))

        console.print(f"[green]✓ Found {len(unique_images)} unique images[/green]")
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
        all_containers = soup.find_all(['div', 'article', 'section'])

        candidates = []
        for container in all_containers:
            # Skip excluded containers
            if any(container.select(ex_sel) for ex_sel in exclude_selectors):
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

    def _get_best_image_url(self, img_tag, base_url: str) -> Optional[str]:
        """Get the highest quality image URL from an img tag"""
        # Priority: data-src, data-original, src
        candidates = [
            img_tag.get('data-src'),
            img_tag.get('data-original'),
            img_tag.get('data-full'),
            img_tag.get('data-large'),
            img_tag.get('srcset', '').split(',')[0].split()[0] if img_tag.get('srcset') else None,
            img_tag.get('src'),
        ]

        for url in candidates:
            if url and self._is_image_url(url):
                return urljoin(base_url, url)

        return None

    async def _find_large_images(self, page: Page, base_url: str) -> List[str]:
        """Find all large images on the page using JavaScript"""
        images = await page.evaluate("""
            () => {
                const images = [];
                const imgElements = document.querySelectorAll('img');

                imgElements.forEach(img => {
                    // Get natural dimensions
                    if (img.naturalWidth >= 500 && img.naturalHeight >= 500) {
                        // Try to get highest quality source
                        const src = img.dataset.src || img.dataset.original ||
                                   img.dataset.full || img.dataset.large || img.src;
                        if (src && !src.includes('data:image')) {
                            images.push(src);
                        }
                    }
                });

                return images;
            }
        """)

        # Convert to absolute URLs
        return [urljoin(base_url, img) for img in images if self._is_image_url(img)]

    @staticmethod
    def _is_image_url(url: str) -> bool:
        """Check if URL is likely an image"""
        if not url:
            return False

        # Remove query parameters for extension check
        url_path = urlparse(url).path.lower()
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
        return url_path.endswith(image_extensions)

    async def detect_next_page(self, page: Page) -> Optional[str]:
        """Detect next page URL for pagination"""
        if not self.detection_config.get('detect_pagination', True):
            return None

        selectors = self.detection_config.get('pagination_selectors', [])

        for selector in selectors:
            try:
                next_link = await page.query_selector(selector)
                if next_link:
                    href = await next_link.get_attribute('href')
                    if href:
                        return urljoin(page.url, href)
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

        # Check dimensions
        try:
            img = Image.open(io.BytesIO(content))
            width, height = img.size

            if width < self.min_width or height < self.min_height:
                return False

            return True
        except Exception:
            return False

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


class GalleryScraper:
    """Main scraper class"""

    def __init__(self, config_path: str = 'config.yaml'):
        self.config = self._load_config(config_path)
        self.detector = GalleryDetector(self.config)
        self.downloader = ImageDownloader(self.config)

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    async def scrape_gallery(self, url: str, output_dir: Optional[Path] = None):
        """Scrape a single gallery"""
        console.print(Panel.fit(
            f"[bold cyan]🚀 Starting Gallery Scraper[/bold cyan]\n[white]URL: {url}[/white]",
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

        # Start browser
        async with async_playwright() as p:
            browser = await self._launch_browser(p)
            page = await browser.new_page()

            try:
                # Navigate to page
                console.print(f"[cyan]🌐 Loading page...[/cyan]")
                await page.goto(url, timeout=self.config['scraper']['page_timeout'])

                all_images = []
                page_num = 1
                max_pages = self.config['detection'].get('max_pages', 100)
                current_url = url
                visited_urls = set()

                # Collect images from all pages
                while current_url and page_num <= max_pages:
                    if current_url in visited_urls:
                        break

                    visited_urls.add(current_url)

                    if page_num > 1:
                        console.print(f"\n[cyan]📄 Loading page {page_num}...[/cyan]")
                        await page.goto(current_url, timeout=self.config['scraper']['page_timeout'])

                    # Detect images
                    images = await self.detector.detect_gallery_images(page, current_url)
                    all_images.extend(images)

                    # Check for next page
                    if self.config['detection'].get('detect_pagination', True):
                        next_url = await self.detector.detect_next_page(page)
                        if next_url and next_url != current_url:
                            current_url = next_url
                            page_num += 1
                        else:
                            break
                    else:
                        break

                # Remove duplicates
                unique_images = list(dict.fromkeys(all_images))

                console.print(f"\n[bold green]✓ Total images found: {len(unique_images)}[/bold green]")
                console.print(f"[bold green]✓ Pages scraped: {page_num}[/bold green]\n")

                if not unique_images:
                    console.print("[yellow]⚠ No images found![/yellow]")
                    return

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
                        total=len(unique_images)
                    )

                    stats = await self.downloader.download_images(
                        unique_images,
                        output_dir,
                        progress,
                        task
                    )

                # Show summary
                self._show_summary(stats, output_dir)

            finally:
                await browser.close()

    async def _launch_browser(self, playwright) -> Browser:
        """Launch browser with configured settings"""
        browser_type = self.config['scraper'].get('browser_type', 'chromium')
        headless = self.config['scraper'].get('headless', True)

        browser_launcher = getattr(playwright, browser_type)

        launch_options = {
            'headless': headless
        }

        # Custom user agent
        user_agent = self.config['scraper'].get('user_agent')
        if user_agent:
            launch_options['user_agent'] = user_agent

        return await browser_launcher.launch(**launch_options)

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

    async def scrape_multiple(self, urls: List[str]):
        """Scrape multiple galleries from a list of URLs"""
        console.print(Panel.fit(
            f"[bold cyan]🚀 Batch Scraper[/bold cyan]\n[white]Total galleries: {len(urls)}[/white]",
            border_style="cyan"
        ))

        for i, url in enumerate(urls, 1):
            console.print(f"\n[bold cyan]═══ Gallery {i}/{len(urls)} ═══[/bold cyan]\n")
            try:
                await self.scrape_gallery(url)
            except Exception as e:
                console.print(f"[red]✗ Error scraping {url}: {e}[/red]")
                continue

        console.print(f"\n[bold green]✨ All galleries processed![/bold green]\n")


@click.group()
def cli():
    """Intelligent Adult Content Gallery Scraper"""
    pass


@cli.command()
@click.argument('url')
@click.option('--output', '-o', help='Output directory', type=click.Path())
@click.option('--config', '-c', default='config.yaml', help='Config file path')
def scrape(url: str, output: Optional[str], config: str):
    """Scrape a single gallery from URL"""
    scraper = GalleryScraper(config)
    output_dir = Path(output) if output else None
    asyncio.run(scraper.scrape_gallery(url, output_dir))


@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--config', '-c', default='config.yaml', help='Config file path')
def batch(file: str, config: str):
    """Scrape multiple galleries from a file (one URL per line)"""
    with open(file, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    scraper = GalleryScraper(config)
    asyncio.run(scraper.scrape_multiple(urls))


@cli.command()
def init():
    """Initialize Playwright browsers"""
    console.print("[cyan]Installing Playwright browsers...[/cyan]")
    import subprocess
    subprocess.run(['playwright', 'install', 'chromium'])
    console.print("[green]✓ Done! You can now use the scraper.[/green]")


if __name__ == '__main__':
    cli()
