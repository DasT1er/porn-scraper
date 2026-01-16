#!/usr/bin/env python3
"""
Interactive UI for Gallery Scraper
Beautiful terminal interface with menus and auto-category scraping
"""

import asyncio
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin, urlparse
import re

import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.prompt import Prompt, Confirm
import requests
from bs4 import BeautifulSoup

# Import our existing scraper
from scraper_v2 import HybridScraper, console as scraper_console


# Custom style for questionary
custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),
    ('question', 'bold'),
    ('answer', 'fg:#f44336 bold'),
    ('pointer', 'fg:#673ab7 bold'),
    ('highlighted', 'fg:#673ab7 bold'),
    ('selected', 'fg:#cc5454'),
    ('separator', 'fg:#cc5454'),
    ('instruction', ''),
    ('text', ''),
    ('disabled', 'fg:#858585 italic')
])

console = Console()


class CategoryDetector:
    """Detects and extracts gallery links from category pages"""

    def __init__(self, config_path: str = 'config.yaml'):
        self.scraper = HybridScraper(config_path)

    def detect_gallery_links(self, category_url: str, max_pages: int = 10) -> List[str]:
        """
        Extract all gallery links from a category page

        Args:
            category_url: URL of the category page
            max_pages: Maximum number of category pages to scan

        Returns:
            List of gallery URLs found
        """
        console.print(Panel.fit(
            f"[bold cyan]🔍 Scanning Category[/bold cyan]\n[white]{category_url}[/white]",
            border_style="cyan"
        ))

        all_gallery_links = []
        visited_urls = set()
        current_url = category_url
        page_num = 1

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        while current_url and page_num <= max_pages:
            if current_url in visited_urls:
                break

            visited_urls.add(current_url)

            try:
                console.print(f"[cyan]📄 Scanning page {page_num}...[/cyan]")

                # Fetch category page
                response = requests.get(current_url, headers=headers, timeout=30)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract gallery links
                gallery_links = self._extract_gallery_links(soup, current_url)

                console.print(f"[green]✓ Found {len(gallery_links)} galleries on page {page_num}[/green]")
                all_gallery_links.extend(gallery_links)

                # Check for next page
                next_url = self._find_next_category_page(soup, current_url)

                if next_url and next_url != current_url:
                    current_url = next_url
                    page_num += 1
                else:
                    break

            except Exception as e:
                console.print(f"[red]✗ Error scanning page {page_num}: {e}[/red]")
                break

        # Remove duplicates
        unique_galleries = list(dict.fromkeys(all_gallery_links))

        console.print(f"\n[bold green]✓ Total galleries found: {len(unique_galleries)}[/bold green]\n")

        return unique_galleries

    def _extract_gallery_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract gallery links from category page"""
        gallery_links = []

        # Common patterns for gallery links
        patterns = [
            # Links with /gallery/, /comic/, /porncomic/, etc.
            r'/(gallery|comic|porncomic|comics|album|post|galls|pics)/[^"\']+',
            # Links that look like gallery IDs
            r'/\d{5,}/[^"\']*',
        ]

        # Find all links
        all_links = soup.find_all('a', href=True)

        for link in all_links:
            href = link.get('href', '')

            # Skip empty or anchor links
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue

            # Check if link matches gallery patterns
            for pattern in patterns:
                if re.search(pattern, href):
                    full_url = urljoin(base_url, href)

                    # Avoid pagination links, filter links, etc.
                    if not self._is_excluded_link(full_url):
                        gallery_links.append(full_url)
                    break

        # Also try to find links in specific containers
        gallery_containers = soup.select('.gallery, .post, .item, .comic, .thumb, article')

        for container in gallery_containers:
            link = container.find('a', href=True)
            if link:
                href = link.get('href', '')
                if href and not href.startswith('#'):
                    full_url = urljoin(base_url, href)
                    if not self._is_excluded_link(full_url):
                        gallery_links.append(full_url)

        return gallery_links

    def _is_excluded_link(self, url: str) -> bool:
        """Check if link should be excluded"""
        # Exclude pagination, filters, sorts, etc.
        excluded_patterns = [
            r'[?&]page=',
            r'[?&]sort=',
            r'[?&]filter=',
            r'[?&]tag=',
            r'/page/\d+/?$',
            r'/tag/',
            r'/category/',
            r'/search',
            r'/login',
            r'/register',
        ]

        for pattern in excluded_patterns:
            if re.search(pattern, url):
                return True

        return False

    def _find_next_category_page(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """Find next page in category pagination"""
        # Common pagination selectors
        selectors = [
            'a.next',
            'a[rel="next"]',
            '.pagination a:contains("Next")',
            '.pagination a:contains("»")',
            '.pagination a:contains(">")',
            'a.nextpostslink',
        ]

        for selector in selectors:
            try:
                if ':contains' in selector:
                    # For :contains, find all links and check text
                    base_selector = selector.split(':contains')[0]
                    text = selector.split('("')[1].split('")')[0]
                    links = soup.select(base_selector)
                    for link in links:
                        if text in link.get_text():
                            href = link.get('href')
                            if href:
                                return urljoin(current_url, href)
                else:
                    next_link = soup.select_one(selector)
                    if next_link:
                        href = next_link.get('href')
                        if href:
                            return urljoin(current_url, href)
            except Exception:
                continue

        return None


class InteractiveScraper:
    """Interactive terminal UI for the scraper"""

    def __init__(self):
        self.scraper = HybridScraper()
        self.category_detector = CategoryDetector()

    def show_banner(self):
        """Show welcome banner"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🎯  INTELLIGENT GALLERY SCRAPER V2 - INTERACTIVE UI  🎯   ║
║                                                              ║
║              Beautiful • Fast • Intelligent                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """
        console.print(banner, style="bold cyan")

    def main_menu(self):
        """Show main menu"""
        choices = [
            "📷 Scrape Single Gallery",
            "📁 Scrape Entire Category (Auto)",
            "📋 Batch Scrape from File",
            "⚙️  Settings",
            "❌ Exit"
        ]

        return questionary.select(
            "What would you like to do?",
            choices=choices,
            style=custom_style
        ).ask()

    def get_scrape_mode(self):
        """Get scraping mode from user"""
        return questionary.select(
            "Select scraping mode:",
            choices=[
                "⚡ Auto (Fast → Browser fallback)",
                "🚀 Light Mode (Fast, simple sites only)",
                "🌐 Browser Mode (Slower, works everywhere)"
            ],
            style=custom_style
        ).ask()

    def mode_to_string(self, mode_choice: str) -> str:
        """Convert mode choice to mode string"""
        if "Auto" in mode_choice:
            return "auto"
        elif "Light" in mode_choice:
            return "light"
        else:
            return "browser"

    def scrape_single_gallery(self):
        """Scrape a single gallery"""
        console.print()
        url = questionary.text(
            "Enter gallery URL:",
            style=custom_style
        ).ask()

        if not url:
            return

        mode_choice = self.get_scrape_mode()
        mode = self.mode_to_string(mode_choice)

        console.print()
        asyncio.run(self.scraper.scrape_gallery(url, mode=mode))

        console.print("\n[green]✓ Gallery scraping complete![/green]\n")
        input("Press Enter to continue...")

    def scrape_category(self):
        """Scrape entire category"""
        console.print()
        category_url = questionary.text(
            "Enter category URL (e.g., https://multporn.net/comics):",
            style=custom_style
        ).ask()

        if not category_url:
            return

        max_pages = questionary.text(
            "Max category pages to scan (default: 10):",
            default="10",
            style=custom_style
        ).ask()

        try:
            max_pages = int(max_pages)
        except:
            max_pages = 10

        console.print()

        # Detect all galleries in category
        gallery_links = self.category_detector.detect_gallery_links(category_url, max_pages)

        if not gallery_links:
            console.print("[yellow]⚠ No galleries found in category![/yellow]\n")
            input("Press Enter to continue...")
            return

        # Show summary
        table = Table(title="Found Galleries", box=box.ROUNDED, border_style="cyan")
        table.add_column("Nr.", style="cyan", width=6)
        table.add_column("Gallery URL", style="white")

        for i, url in enumerate(gallery_links[:10], 1):  # Show first 10
            table.add_row(str(i), url)

        if len(gallery_links) > 10:
            table.add_row("...", f"... and {len(gallery_links) - 10} more")

        console.print(table)
        console.print()

        # Confirm scraping
        confirm = questionary.confirm(
            f"Scrape all {len(gallery_links)} galleries?",
            default=True,
            style=custom_style
        ).ask()

        if not confirm:
            return

        mode_choice = self.get_scrape_mode()
        mode = self.mode_to_string(mode_choice)

        console.print()

        # Scrape all galleries
        for i, url in enumerate(gallery_links, 1):
            console.print(f"\n[bold cyan]═══ Gallery {i}/{len(gallery_links)} ═══[/bold cyan]\n")
            try:
                asyncio.run(self.scraper.scrape_gallery(url, mode=mode))
            except Exception as e:
                console.print(f"[red]✗ Error: {e}[/red]")
                continue

        console.print("\n[bold green]✨ Category scraping complete![/bold green]\n")
        input("Press Enter to continue...")

    def batch_scrape(self):
        """Batch scrape from file"""
        console.print()
        file_path = questionary.path(
            "Enter path to URL file:",
            style=custom_style
        ).ask()

        if not file_path or not Path(file_path).exists():
            console.print("[red]✗ File not found![/red]\n")
            input("Press Enter to continue...")
            return

        # Read URLs
        with open(file_path, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        console.print(f"\n[cyan]Found {len(urls)} URLs in file[/cyan]\n")

        mode_choice = self.get_scrape_mode()
        mode = self.mode_to_string(mode_choice)

        asyncio.run(self.scraper.scrape_multiple(urls, mode=mode))

        console.print("\n[green]✓ Batch scraping complete![/green]\n")
        input("Press Enter to continue...")

    def show_settings(self):
        """Show settings menu"""
        console.print("\n[bold cyan]⚙️  Settings[/bold cyan]\n")
        console.print("[yellow]Settings are configured in config.yaml[/yellow]")
        console.print("[yellow]Edit the file to change settings[/yellow]\n")

        table = Table(box=box.ROUNDED, border_style="cyan")
        table.add_column("Setting", style="cyan")
        table.add_column("Description", style="white")

        table.add_row("output_dir", "Download location (default: ./downloads)")
        table.add_row("headless", "Run browser invisibly (default: true)")
        table.add_row("min_image_size", "Minimum image size in KB (default: 50)")
        table.add_row("max_concurrent", "Parallel downloads (default: 5)")

        console.print(table)
        console.print()
        input("Press Enter to continue...")

    def run(self):
        """Main run loop"""
        self.show_banner()

        while True:
            choice = self.main_menu()

            if not choice or "Exit" in choice:
                console.print("\n[cyan]👋 Goodbye![/cyan]\n")
                break

            if "Single Gallery" in choice:
                self.scrape_single_gallery()
            elif "Entire Category" in choice:
                self.scrape_category()
            elif "Batch Scrape" in choice:
                self.batch_scrape()
            elif "Settings" in choice:
                self.show_settings()


def main():
    """Entry point"""
    try:
        scraper = InteractiveScraper()
        scraper.run()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]⚠ Interrupted by user[/yellow]\n")
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]\n")


if __name__ == '__main__':
    main()
