#!/usr/bin/env python3
"""
Intelligent Adult Content Gallery Scraper - Hybrid Version
Automatically detects and downloads image galleries and comics
Uses Requests for simple pages, Playwright for JavaScript-heavy pages
"""

import asyncio
import re
import time
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Set, Tuple
from urllib.parse import urljoin, urlparse
import hashlib

# Set Playwright browsers path for portable .exe builds
# This must be done BEFORE importing playwright
if getattr(sys, 'frozen', False):
    # Running as .exe
    bundle_dir = sys._MEIPASS
    exe_dir = os.path.dirname(sys.executable)

    # Check for bundled Chromium in multiple locations
    possible_browser_paths = [
        os.path.join(exe_dir, 'playwright_browsers'),        # Created by BUILD_PORTABLE.bat
        os.path.join(exe_dir, '_internal', 'playwright'),
        os.path.join(bundle_dir, 'playwright'),
        os.path.join(exe_dir, 'playwright'),
    ]

    for browser_path in possible_browser_paths:
        if os.path.exists(browser_path):
            os.environ['PLAYWRIGHT_BROWSERS_PATH'] = browser_path
            # Also log it for debugging
            print(f"[DEBUG] Set PLAYWRIGHT_BROWSERS_PATH to: {browser_path}")
            break

# Web scraping
import requests
from bs4 import BeautifulSoup

# Playwright - Modern browser automation (ONLY SYSTEM)
try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    print("=" * 80)
    print("ERROR: Playwright not installed!")
    print("Install with:")
    print("  pip install playwright")
    print("  playwright install chromium")
    print("=" * 80)

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

        # Replace competitor domain mentions in description
        if metadata['description']:
            # Replace full URLs with just "pornypics.net"
            metadata['description'] = re.sub(
                r'https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(?:/[^\s\"\,\}\]]*)?',
                'pornypics.net', metadata['description'])
            # Replace competitor domain text mentions
            for domain in ['pornpics', 'allasianpics', 'lamalinks']:
                metadata['description'] = re.sub(
                    rf'{domain}\.\w+', 'pornypics.net', metadata['description'])

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

        # Words to skip (navigation, common non-tag words)
        skip_words = {
            'tags', 'tag', 'tags:', 'categories:', 'keywords:', 'characters:',
            'more', 'all', 'category', 'categories',
            'home', 'next', 'prev', 'previous', '»', '«', '>', '<',
            'search', 'login', 'register', 'menu',
            'pornstars', 'sex chat', 'horny girls', 'tik tok porn',
            'amateur cams', 'live cams', 'webcams', 'welcome',
            'dmca', 'privacy', 'terms', '2257', 'sitemap',
            'contact', 'about', 'help', 'faq',
        }

        def _is_valid_tag(text):
            text = text.strip()
            if not text or len(text) < 2 or len(text) > 40:
                return False
            if text.isdigit():
                return False
            if text.lower() in skip_words:
                return False
            return True

        def _add_tag(text):
            text = text.strip()
            text = text.replace(',', '').replace(';', '').replace('#', '')
            text = re.sub(r'\s+', ' ', text)
            if _is_valid_tag(text) and text not in tags:
                tags.append(text)

        # Strategy 1: Find links with tag-like URL patterns
        try:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')

                # Skip person/model links (class="person", data-models attribute)
                link_classes = link.get('class', [])
                if 'person' in link_classes or link.get('data-models'):
                    continue

                # Skip model/pornstar URL patterns - these are people, not tags
                if any(p in href for p in ['/pornstars/', '/pornstar/', '/models/', '/model/',
                                           '/actress/', '/performers/', '/performer/']):
                    continue

                # Direct match patterns (high confidence)
                if any(p in href for p in ['/category/', '/tag/', '/user_tags/', '/tags/', '/labels/', '/niches/']):
                    _add_tag(link.get_text())
                    continue

                # Pattern with filtering: /pics/, /galleries/, /channels/
                # Only match short path segments (tag names, not gallery slugs)
                for prefix in ['/pics/', '/galleries/', '/channels/']:
                    if prefix in href:
                        # Extract path segment after prefix
                        idx = href.index(prefix) + len(prefix)
                        remaining = href[idx:].strip('/')
                        # Tag URLs have short slugs, gallery URLs have long slugs with many dashes
                        if remaining and len(remaining) < 25 and remaining.count('-') < 3:
                            _add_tag(link.get_text())
                        break
        except:
            pass

        # Strategy 2: Common tag CSS selectors (including porn site specific ones)
        tag_selectors = [
            # Generic
            '.tags a',
            '.tag',
            '.post-tag',
            'a[rel="tag"]',
            '.label',
            '.badge',
            # Porn site specific
            '.content-categories a:not(.person)',  # allasianpics, lamalinks
            '.bot a',  # multporn.net uses this!
            '.wp-tag-cloud a',  # WordPress tag cloud
            '.tagcloud a',
            '.entry-tags a',
            '.post-tags a',
            'a.tag-link',
            'a.tag_item',
            # Additional common selectors
            '.tag-list a',
            '.tags-list a',
            '.tag-container a',
            '.tdn a',
            '.info-tags a',
            '.meta-tags a',
            '.categories-list a',
            '.cats a',
            '.cat-list a',
            # By pattern matching
            'a[href*="/tag/"]',
            'a[href*="/tags/"]',
        ]

        for selector in tag_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    # Skip person/model links (e.g. class="person", data-models attr)
                    if elem.get('class') and 'person' in elem.get('class', []):
                        continue
                    if elem.get('data-models'):
                        continue
                    _add_tag(elem.get_text())
            except:
                continue

        # Strategy 3: Heuristic - ALWAYS run as primary detection method
        # Detects tags by page structure: a group of short-text elements in a container
        # Works for sites like lamalinks.com, allasianpics.com where tags are visible
        # on the page but don't use recognizable URL patterns
        heuristic_tags = self._heuristic_tag_extraction(soup)
        for tag in heuristic_tags:
            _add_tag(tag)

        return tags[:50]  # Limit to 50 tags

    def _heuristic_tag_extraction(self, soup: BeautifulSoup) -> List[str]:
        """Find tags by detecting grouped short-text elements on the page.

        Uses multiple signals to distinguish real tag bars from directory sections:
        - "Tags:" label nearby = very strong positive
        - Link URLs pointing to /models/, /pornstars/ = strong negative
        - Link URLs pointing to /tags/, /category/ = strong positive
        - Person name pattern (Firstname Lastname) = negative
        - Directory heading/label nearby = strong negative
        - Large item count (30+) = negative
        - Tag-related CSS class = positive
        """
        import re as _re

        nav_words = {
            'home', 'about', 'contact', 'login', 'register', 'sign in', 'sign up',
            'search', 'pornstars', 'sex chat', 'horny girls',
            'tik tok porn', 'amateur cams', 'live cams', 'webcams',
            'dmca', 'privacy', 'terms', '2257', 'sitemap',
            'welcome', 'help', 'faq', 'menu', 'rss',
        }

        # Words that indicate directory/listing sections (NOT gallery tags)
        directory_words = [
            'trending', 'related', 'popular', 'view more', 'more tags',
            'more pornstar', 'more categor', 'more model',
            'favourite', 'favorite', 'featured', 'suggested', 'recommended',
            'top pornstar', 'top model', 'top artist',
            'all pornstar', 'all model', 'all artist', 'all tag', 'all categor',
            'similar', 'you may', 'you might', 'best pornstar', 'best model',
            'pornstar list', 'model list', 'artist list',
        ]

        # Words in class/id that indicate directory sections
        directory_class_words = [
            'trending', 'related', 'popular', 'sidebar', 'suggested',
            'recommended', 'similar', 'favourite', 'favorite', 'featured',
            'pornstar', 'model-list', 'artist',
        ]

        # URL path segments that indicate model/pornstar links
        model_url_patterns = [
            '/models/', '/model/', '/pornstars/', '/pornstar/',
            '/actress/', '/girls/', '/girl/', '/artists/', '/artist/',
            '/performers/', '/performer/', '/stars/', '/star/',
        ]

        # URL path segments that indicate tag/category links
        tag_url_patterns = [
            '/tags/', '/tag/', '/category/', '/categories/',
            '/cat/', '/keywords/', '/keyword/', '/niches/', '/niche/',
        ]

        # --- Pre-compute gallery image position ---
        all_elems = soup.find_all(True)
        elem_pos = {id(e): i for i, e in enumerate(all_elems)}

        gallery_pos = len(all_elems)
        img_positions = [i for i, e in enumerate(all_elems) if e.name == 'img']
        for idx in range(len(img_positions) - 2):
            if img_positions[idx + 2] - img_positions[idx] < 30:
                gallery_pos = img_positions[idx]
                break

        # Person name regex: 2-3 capitalized words (like "Arisa Nakano")
        person_name_re = _re.compile(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}$')

        # --- Score each candidate container ---
        best_tags = []
        best_score = 0

        for container in soup.find_all(['div', 'ul', 'ol', 'span', 'section', 'p', 'nav']):
            all_descendants = container.find_all(True)
            if len(all_descendants) > 150:
                continue

            # Collect direct child elements
            child_elements = []
            for child in container.children:
                if hasattr(child, 'name') and child.name:
                    child_elements.append(child)

            # Handle ul > li > a pattern
            if child_elements and sum(1 for c in child_elements if c.name == 'li') > len(child_elements) * 0.5:
                unwrapped = []
                for li in child_elements:
                    if li.name == 'li':
                        inner = li.find(['a', 'span'])
                        unwrapped.append(inner if inner else li)
                    else:
                        unwrapped.append(li)
                child_elements = unwrapped

            if len(child_elements) < 3:
                continue

            # Analyze children
            valid_tags = []
            nav_count = 0
            img_count = 0
            hrefs = []

            for child in child_elements:
                if child is None:
                    continue
                text = child.get_text().strip()
                if not text or len(text) > 35 or text.isdigit():
                    continue
                if child.find('img') and len(text) < 2:
                    img_count += 1
                    continue
                if text.lower() in nav_words:
                    nav_count += 1
                    continue
                # Skip person/model entries (class="person", data-models attr)
                child_classes = child.get('class', []) if hasattr(child, 'get') else []
                if 'person' in child_classes:
                    continue
                if hasattr(child, 'get') and child.get('data-models'):
                    continue
                href = child.get('href', '') if child.name == 'a' else ''
                if href and any(ext in href.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    continue
                valid_tags.append(text)
                if href:
                    hrefs.append(href.lower())

            if len(valid_tags) < 5:
                continue
            if nav_count > len(valid_tags):
                continue
            if img_count > len(valid_tags):
                continue

            # ============ MULTI-SIGNAL SCORING ============
            n = len(valid_tags)
            score = 100  # Base score

            # --- Signal 1: "Tags:" / "Categories:" label nearby ---
            has_tag_label = False
            tag_label_words = ['tags:', 'tags', 'categories:', 'categories',
                               'keywords:', 'keywords', 'characters:']
            # Check inline text in container or parent
            for check_elem in [container, container.parent]:
                if not check_elem:
                    continue
                for child_node in check_elem.children:
                    if isinstance(child_node, str):
                        txt = child_node.strip().lower()
                        if txt in tag_label_words:
                            has_tag_label = True
                            break
                    elif hasattr(child_node, 'name') and child_node.name in ['strong', 'b', 'span', 'label', 'em']:
                        txt = child_node.get_text().strip().lower()
                        if txt in tag_label_words:
                            has_tag_label = True
                            break
                if has_tag_label:
                    break
            # Also check previous sibling
            if not has_tag_label:
                prev = container.find_previous_sibling()
                if prev:
                    pt = prev.get_text().strip().lower()
                    if pt in tag_label_words:
                        has_tag_label = True

            if has_tag_label:
                score += 500

            # --- Signal 2: Link URL patterns ---
            if hrefs:
                model_link_count = sum(1 for h in hrefs if any(p in h for p in model_url_patterns))
                tag_link_count = sum(1 for h in hrefs if any(p in h for p in tag_url_patterns))

                if model_link_count > len(hrefs) * 0.3:
                    score -= 600  # Strong negative: links point to model/pornstar pages
                if tag_link_count > len(hrefs) * 0.3:
                    score += 300  # Strong positive: links point to tag/category pages

            # --- Signal 3: Person name detection ---
            if valid_tags:
                name_count = sum(1 for t in valid_tags if person_name_re.match(t))
                name_ratio = name_count / len(valid_tags)
                if name_ratio > 0.5:
                    score -= 400  # Most items look like person names

            # --- Signal 4: DOM position (before gallery = moderate bonus) ---
            container_pos = elem_pos.get(id(container), len(all_elems))
            if container_pos < gallery_pos:
                score += 100

            # --- Signal 5: Nearby directory headings/labels = strong penalty ---
            is_directory = False

            # Check class/id of container and ancestors
            for elem in [container, container.parent,
                         container.parent.parent if container.parent else None]:
                if not elem or not hasattr(elem, 'get'):
                    continue
                attrs = ''
                for attr in ['class', 'id']:
                    val = elem.get(attr, '')
                    attrs += (' '.join(val) if isinstance(val, list) else str(val)) + ' '
                if any(w in attrs.lower() for w in directory_class_words):
                    is_directory = True
                    break

            # Broad text search: check ANY element near the container for directory words
            # This catches headings inside wrapper divs, <span>, <strong>, etc.
            if not is_directory:
                # Check preceding siblings of container and its parent (any element, not just headings)
                for check in [container, container.parent]:
                    if not check or not hasattr(check, 'find_previous_sibling'):
                        continue
                    for sib in check.previous_siblings:
                        if not hasattr(sib, 'get_text'):
                            continue
                        sib_text = sib.get_text().strip().lower()
                        if len(sib_text) > 100:
                            break  # Stop at large content blocks
                        if any(w in sib_text for w in directory_words):
                            is_directory = True
                            break
                    if is_directory:
                        break

                # Check headings inside parent wrapper
                if not is_directory:
                    for check in [container, container.parent]:
                        if not check or not hasattr(check, 'parent') or not check.parent:
                            continue
                        parent = check.parent
                        if hasattr(parent, 'find_all'):
                            for child in parent.find_all(True, recursive=False):
                                if child == check or child == container:
                                    continue
                                txt = child.get_text().strip().lower()
                                if len(txt) < 80 and any(w in txt for w in directory_words):
                                    is_directory = True
                                    break
                        if is_directory:
                            break

            if is_directory:
                score -= 500

            # --- Signal 6: Item count preference ---
            if n <= 20:
                score += 30  # Typical tag bar size
            elif n > 30:
                score -= 100  # Too many items = likely directory

            # --- Signal 7: Tag-related CSS class names ---
            for elem in [container, container.parent]:
                if elem and hasattr(elem, 'get'):
                    classes = ' '.join(elem.get('class', []))
                    if any(w in classes.lower() for w in ['tag', 'cat', 'label', 'info', 'meta', 'keyword', 'badge']):
                        score += 200
                        break

            # --- Penalty for header/footer ---
            for parent in container.parents:
                if parent and parent.name in ['header', 'footer']:
                    score //= 3
                    break

            if score > best_score:
                best_score = score
                best_tags = valid_tags

        return best_tags

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
        """Detect all gallery images from HTML (works with both Requests and Playwright)"""
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

    def detect_gallery_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Detect all gallery images from BeautifulSoup object (wrapper for Playwright compatibility)"""
        # Convert soup to HTML string and use existing method
        html = str(soup)
        return self.detect_gallery_images_html(html, base_url)

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
        """Extract all image URLs from a container.
        Prefers full-size URLs from <a href> over thumbnail URLs from <img src>.
        When <a> wraps <img>, uses the link URL (full-size) and skips the img (thumbnail).
        """
        images = []
        seen_urls = set()
        thumbnail_urls = set()  # Track thumbnails that have a full-size link

        # Pass 1: Find <a> tags that link to images - these are full-size URLs
        for link in container.find_all('a'):
            href = link.get('href', '')
            if self._is_image_url(href):
                full_url = urljoin(base_url, href)
                if full_url not in seen_urls:
                    images.append(full_url)
                    seen_urls.add(full_url)
                    # Mark any <img> inside this <a> as a thumbnail (skip later)
                    for img in link.find_all('img'):
                        thumb_url = self._get_best_image_url(img, base_url)
                        if thumb_url:
                            thumbnail_urls.add(thumb_url)

        # Pass 2: Find <img> tags NOT already covered by <a> links
        for img in container.find_all('img'):
            img_url = self._get_best_image_url(img, base_url)
            if img_url and img_url not in seen_urls and img_url not in thumbnail_urls:
                images.append(img_url)
                seen_urls.add(img_url)

        return images

    def _find_all_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find all images on the page.
        Same logic: prefers <a href> full-size over <img src> thumbnails.
        """
        images = []
        seen_urls = set()
        thumbnail_urls = set()

        # Pass 1: <a> links to images (full-size)
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if self._is_image_url(href):
                full_url = urljoin(base_url, href)
                if full_url not in seen_urls:
                    images.append(full_url)
                    seen_urls.add(full_url)
                    for img in link.find_all('img'):
                        thumb_url = self._get_best_image_url(img, base_url)
                        if thumb_url:
                            thumbnail_urls.add(thumb_url)

        # Pass 2: <img> tags not covered by <a> links
        for img in soup.find_all('img'):
            img_url = self._get_best_image_url(img, base_url)
            if img_url and img_url not in seen_urls and img_url not in thumbnail_urls:
                images.append(img_url)
                seen_urls.add(img_url)

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
        self.min_size = config['scraper'].get('min_image_size', 15) * 1024  # KB to bytes
        self.min_width = config['scraper'].get('min_width', 400)
        self.min_height = config['scraper'].get('min_height', 400)

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
    """Hybrid scraper that tries Requests first, falls back to Playwright"""

    def __init__(self, config_path: str = 'config.yaml'):
        self.config = self._load_config(config_path)
        self.detector = GalleryDetector(self.config)
        self.downloader = ImageDownloader(self.config)
        self.metadata_extractor = MetadataExtractor(self.config)

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from YAML file or use defaults"""
        import sys
        import os

        # Default configuration (fallback if config.yaml not found)
        default_config = {
            'download': {
                'output_dir': 'downloads',
                'threads': 5,
                'timeout': 30,
                'retry_attempts': 3
            },
            'scraper': {
                'default_mode': 'auto',
                'min_images_threshold': 5,
                'headless': True,
                'page_load_wait': 3,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            'detection': {
                'min_image_size': 50000,
                'detect_pagination': True,
                'max_pages': 100,
                'gallery_selectors': [
                    '.gallery', '#gallery', '.comic', '.pages',
                    '[class*="gallery"]', '[id*="gallery"]'
                ],
                'exclude_selectors': [
                    '.sidebar', '.navigation', '.menu', '.footer',
                    '.header', '.ad', '.advertisement'
                ]
            },
            'metadata': {
                'save_metadata': True,
                'extract_title': True,
                'extract_tags': True,
                'extract_artist': True
            }
        }

        # Try to find config.yaml in different locations
        config_locations = []

        # If running as PyInstaller bundle
        if getattr(sys, 'frozen', False):
            # Running as .exe
            bundle_dir = sys._MEIPASS
            exe_dir = os.path.dirname(sys.executable)
            config_locations = [
                os.path.join(exe_dir, config_path),
                os.path.join(bundle_dir, config_path),
                config_path
            ]
        else:
            # Running as script
            config_locations = [config_path]

        # Try each location
        for location in config_locations:
            if os.path.exists(location):
                try:
                    with open(location, 'r', encoding='utf-8') as f:
                        loaded_config = yaml.safe_load(f)
                        console.print(f"[dim]Loaded config from: {location}[/dim]")
                        return loaded_config
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not load {location}: {e}[/yellow]")
                    continue

        # If no config found, use defaults
        console.print("[yellow]⚠ config.yaml not found, using default configuration[/yellow]")
        return default_config

    async def scrape_gallery(self, url: str, output_dir: Optional[Path] = None, mode: str = 'auto', _from_listing: bool = False):
        """
        Scrape a single gallery

        Args:
            url: Gallery URL
            output_dir: Output directory
            mode: 'auto' (try requests first), 'light' (requests only), 'browser' (playwright only)
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
                console.print("[cyan]🌐 Switching to Browser Mode (Playwright)...[/cyan]")
            else:
                console.print("[cyan]🌐 Using Browser Mode (Playwright)...[/cyan]")

            # Use Playwright (ONLY system)
            if not HAS_PLAYWRIGHT:
                console.print("[red]✗ Playwright not installed![/red]")
                console.print("[yellow]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/yellow]")
                console.print("[yellow]Install Playwright:[/yellow]")
                console.print("[yellow]   pip install playwright[/yellow]")
                console.print("[yellow]   playwright install chromium[/yellow]")
                console.print("[yellow]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/yellow]")
                return

            all_images = await self._scrape_with_playwright(url)

        # Check if this is a listing/category page (before downloading images)
        if not _from_listing:
            # Quick HTML fetch to check page structure
            listing_soup = None
            try:
                headers = {'User-Agent': self.config['scraper'].get('user_agent', 'Mozilla/5.0')}
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    listing_soup = BeautifulSoup(resp.text, 'html.parser')
            except Exception:
                pass

            if listing_soup and self._is_listing_page(listing_soup, url):
                console.print("[cyan]🔍 Detected listing/category page with gallery grid![/cyan]")
                listing_handled = await self._try_as_listing_page(url, output_dir, mode)
                if listing_handled:
                    return

        if not all_images:
            # Before giving up, also check if this is a listing/category page
            if not _from_listing:
                listing_handled = await self._try_as_listing_page(url, output_dir, mode)
                if listing_handled:
                    return

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

    def _ensure_playwright_browsers(self):
        """Ensure Playwright browsers are installed, install if missing"""
        import subprocess
        import sys
        import os

        try:
            # FIRST: Check if we have a portable browser via PLAYWRIGHT_BROWSERS_PATH
            browsers_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH')
            if browsers_path and os.path.exists(browsers_path):
                # Check if chromium folder exists in there
                chromium_path = os.path.join(browsers_path, 'chromium')
                if os.path.exists(chromium_path):
                    # Check for chrome.exe or chrome executable
                    chrome_exe_paths = [
                        os.path.join(chromium_path, 'chrome-win64', 'chrome.exe'),  # Windows
                        os.path.join(chromium_path, 'chrome-linux', 'chrome'),      # Linux
                        os.path.join(chromium_path, 'chrome-mac', 'Chromium.app'),  # Mac
                    ]

                    for chrome_exe in chrome_exe_paths:
                        if os.path.exists(chrome_exe):
                            console.print(f"[green]✓ Portable Chromium found at: {chrome_exe}[/green]")
                            console.print(f"[dim]Using bundled browser from: {browsers_path}[/dim]")
                            return  # Browser is ready!

            # SECOND: Try to check if chromium is installed normally
            from playwright.sync_api import sync_playwright

            # Quick check: try to get browser executable path
            try:
                with sync_playwright() as p:
                    browser_type = p.chromium
                    # This will raise if browser is not installed
                    executable = browser_type.executable_path

                    # Log where browser was found
                    if os.path.exists(executable):
                        console.print(f"[dim]✓ Chromium browser found at: {executable}[/dim]")
                        return
            except Exception as e:
                console.print(f"[dim]Browser check failed: {e}[/dim]")
                pass

            # Check if we're running as .exe with bundled browsers
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(sys.executable)
                bundled_browser = os.path.join(exe_dir, '_internal', 'playwright', 'chromium')

                if os.path.exists(bundled_browser):
                    console.print(f"[yellow]⚠ Bundled Chromium found but Playwright can't use it[/yellow]")
                    console.print(f"[yellow]Location: {bundled_browser}[/yellow]")
                    console.print(f"[yellow]This is a known issue with portable builds.[/yellow]")
                    console.print(f"[yellow]Attempting automatic installation...[/yellow]\n")

            # Browser not found, install it
            console.print("\n[yellow]════════════════════════════════════════════════════[/yellow]")
            console.print("[yellow]⚠ Playwright browsers not found![/yellow]")
            console.print("[cyan]📥 Installing Chromium browser automatically...[/cyan]")
            console.print("[cyan]This is a one-time setup (takes 2-3 minutes)[/cyan]")
            console.print("[cyan]Please wait, download is running...[/cyan]")
            console.print("[yellow]════════════════════════════════════════════════════[/yellow]\n")

            # Install chromium browser - let output go directly to console
            # This avoids encoding issues on Windows
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    check=True,  # Raises exception if fails
                    timeout=300,  # 5 minutes max
                    # Let output go directly to console to avoid encoding issues
                    stdout=None,
                    stderr=None
                )

                console.print("\n[green]✓ Chromium browser installed successfully![/green]")
                console.print("[dim]Browser is now ready to use.[/dim]\n")

            except subprocess.CalledProcessError as e:
                console.print(f"\n[red]✗ Failed to install Chromium browser (exit code {e.returncode})[/red]")
                console.print("\n[yellow]Manual installation:[/yellow]")
                console.print("[yellow]Open Command Prompt and run:[/yellow]")
                console.print("[cyan]  playwright install chromium[/cyan]\n")
                raise Exception("Browser installation failed")

        except subprocess.TimeoutExpired:
            console.print("\n[red]✗ Browser installation timed out[/red]")
            console.print("[yellow]This can happen with slow internet connection.[/yellow]")
            console.print("\n[yellow]Manual installation:[/yellow]")
            console.print("[yellow]Open Command Prompt and run:[/yellow]")
            console.print("[cyan]  playwright install chromium[/cyan]\n")
            raise
        except Exception as e:
            if "Browser installation failed" not in str(e):
                console.print(f"\n[red]✗ Error ensuring browsers: {e}[/red]")
                console.print("\n[yellow]Manual installation:[/yellow]")
                console.print("[yellow]Open Command Prompt and run:[/yellow]")
                console.print("[cyan]  playwright install chromium[/cyan]\n")
            raise

    async def _scrape_with_playwright(self, url: str) -> List[str]:
        """Scrape using Playwright (modern browser automation)"""
        if not HAS_PLAYWRIGHT:
            console.print("[red]✗ Playwright not installed![/red]")
            console.print("[yellow]Install: pip install playwright && playwright install chromium[/yellow]")
            return []

        # Check if Playwright browsers are installed, install if needed
        self._ensure_playwright_browsers()

        all_images = []

        try:
            async with async_playwright() as p:
                # Check if we have a portable browser
                launch_options = {
                    'headless': self.config['scraper'].get('headless', True),
                    'args': ['--no-sandbox', '--disable-setuid-sandbox']
                }

                # If portable browser exists, use direct executable path
                browsers_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH')
                if browsers_path:
                    chrome_exe = os.path.join(browsers_path, 'chromium', 'chrome-win64', 'chrome.exe')
                    if os.path.exists(chrome_exe):
                        launch_options['executable_path'] = chrome_exe
                        console.print(f"[dim]Using portable browser: {chrome_exe}[/dim]")

                # Launch browser
                browser = await p.chromium.launch(**launch_options)

                # Create context with realistic settings
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=self.config['scraper'].get('user_agent',
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                )

                page = await context.new_page()

                # Navigate to page
                console.print(f"[cyan]Loading page...[/cyan]")
                await page.goto(url, wait_until='networkidle', timeout=30000)

                # Wait for page to load
                await page.wait_for_timeout(self.config['scraper'].get('page_load_wait', 3) * 1000)

                # Scroll to load lazy images
                console.print(f"[cyan]Scrolling to load images...[/cyan]")
                await page.evaluate("""
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
                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Use detector to find images
                detector = GalleryDetector(self.config)
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
                    await page.goto(next_url, wait_until='networkidle', timeout=30000)
                    await page.wait_for_timeout(2000)

                    # Scroll again
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000)

                    html = await page.content()
                    soup = BeautifulSoup(html, 'html.parser')

                    page_images = detector.detect_gallery_images(soup, next_url)
                    console.print(f"[green]✓ Found {len(page_images)} images on page {page_num}[/green]")

                    all_images.extend(page_images)
                    url = next_url
                    page_num += 1

                await browser.close()

        except Exception as e:
            console.print(f"[red]✗ Playwright error: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            console.print(f"[yellow]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/yellow]")
            console.print(f"[yellow]Please report this error if it persists![/yellow]")
            console.print(f"[yellow]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/yellow]")
            return []

        # Remove duplicates
        unique_images = list(dict.fromkeys(all_images))
        return unique_images

    async def _try_as_listing_page(self, url: str, output_dir: Optional[Path], mode: str) -> bool:
        """Check if URL is a listing/category page and scrape galleries from it"""
        console.print("\n[cyan]🔍 Checking if this is a listing/category page...[/cyan]")

        headers = {
            'User-Agent': self.config['scraper'].get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        }

        soup = None

        # Try with Playwright first (better for JS-rendered infinite scroll pages)
        if HAS_PLAYWRIGHT:
            try:
                async with async_playwright() as p:
                    launch_options = {
                        'headless': self.config['scraper'].get('headless', True),
                        'args': ['--no-sandbox', '--disable-setuid-sandbox']
                    }
                    browser = await p.chromium.launch(**launch_options)
                    context = await browser.new_context(
                        viewport={'width': 1920, 'height': 1080},
                        user_agent=headers['User-Agent']
                    )
                    page = await context.new_page()
                    await page.goto(url, wait_until='networkidle', timeout=30000)
                    await page.wait_for_timeout(3000)

                    # Scroll multiple times to load infinite scroll content
                    console.print("[cyan]📜 Scrolling to load galleries...[/cyan]")
                    await self._scroll_page(page, max_scrolls=20)

                    html = await page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    await browser.close()
            except Exception as e:
                console.print(f"[dim]Browser fetch failed: {e}[/dim]")

        # Fallback to requests
        if not soup:
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
            except Exception:
                pass

        if not soup:
            return False

        # Extract gallery links
        gallery_links = self._extract_listing_gallery_links(soup, url)

        if len(gallery_links) < 3:
            return False

        console.print(f"[green]✓ Detected listing page with {len(gallery_links)} galleries![/green]")

        # Show found galleries
        for i, gurl in enumerate(gallery_links[:5], 1):
            console.print(f"[dim]  {i}. {gurl}[/dim]")
        if len(gallery_links) > 5:
            console.print(f"[dim]  ... and {len(gallery_links) - 5} more[/dim]")

        console.print(f"\n[cyan]📥 Scraping all {len(gallery_links)} galleries...[/cyan]")

        # Use passed output_dir or create one
        if output_dir is None:
            output_dir = Path(self.config['download']['output_dir'])
            if self.config['download'].get('create_subdirs', True):
                folder_name = self._generate_folder_name(url)
                output_dir = output_dir / folder_name

        # Scrape each gallery
        for i, gallery_url in enumerate(gallery_links, 1):
            console.print(f"\n[bold cyan]═══ Gallery {i}/{len(gallery_links)} ═══[/bold cyan]")
            console.print(f"[dim]{gallery_url}[/dim]\n")
            try:
                await self.scrape_gallery(gallery_url, output_dir=output_dir, mode=mode, _from_listing=True)
            except Exception as e:
                console.print(f"[red]✗ Error scraping gallery: {e}[/red]")
                continue

        console.print(f"\n[bold green]✨ Listing page complete! ({len(gallery_links)} galleries)[/bold green]")
        return True

    def _is_listing_page(self, soup: BeautifulSoup, url: str) -> bool:
        """Detect if a page is a listing/category page (grid of gallery thumbnails)
        rather than an actual gallery with full-size images.

        Key signal: many <a> tags wrapping <img> thumbnails that link to OTHER internal pages.
        """
        base_domain = urlparse(url).netloc.replace('www.', '')
        base_path = urlparse(url).path.rstrip('/')

        thumb_link_count = 0
        total_images = len(soup.find_all('img'))

        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue

            # Must wrap an image
            if not link.find('img'):
                continue

            full_url = urljoin(url, href)
            link_path = urlparse(full_url).path.rstrip('/')
            link_domain = urlparse(full_url).netloc.replace('www.', '')

            # Must be same domain
            if link_domain != base_domain:
                continue

            # Must link to a different page (not same page, not image file)
            if link_path == base_path:
                continue
            if any(link_path.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                continue

            # Must be longer/deeper than current path (gallery links are more specific)
            if len(link_path) > len(base_path) + 5:
                thumb_link_count += 1

        # If more than 5 thumbnail links to internal pages, it's likely a listing page
        return thumb_link_count >= 5

    def _extract_listing_gallery_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract gallery links from a listing/category page"""
        gallery_links = []
        seen_urls = set()

        base_domain = urlparse(base_url).netloc.replace('www.', '')
        base_path = urlparse(base_url).path.rstrip('/')

        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue

            full_url = urljoin(base_url, href)

            # Skip if already seen
            if full_url in seen_urls:
                continue

            # Skip external links (different domain)
            link_domain = urlparse(full_url).netloc.replace('www.', '')
            if base_domain != link_domain:
                continue

            # Skip if same as current page
            if full_url.rstrip('/') == base_url.rstrip('/'):
                continue

            # Skip excluded patterns (navigation, pagination, etc.)
            if self._is_excluded_listing_link(full_url):
                continue

            # Check if link contains/wraps a thumbnail image
            has_thumb = link.find('img') is not None

            # Check URL patterns for gallery-like links
            path = urlparse(full_url).path
            is_gallery_like = False

            # Gallery URL patterns
            gallery_patterns = [
                r'/(gallery|galleries|comic|comics|album|post|pics|galls)/[^/]{10,}',
                r'/[a-z0-9]+-[a-z0-9-]+-\d{4,}/?$',  # slug-with-numbers pattern
                r'/\d{5,}/',  # numeric ID
            ]

            for pattern in gallery_patterns:
                if re.search(pattern, path):
                    is_gallery_like = True
                    break

            # Links wrapping thumbnails with descriptive slugs
            if not is_gallery_like and has_thumb:
                slug = path.strip('/').split('/')[-1] if '/' in path else path.strip('/')
                # Gallery link: slug longer than 10 chars with dashes (descriptive title)
                if len(slug) > 10 and slug.count('-') >= 2:
                    is_gallery_like = True
                # Gallery link: path is deeper/longer than current page
                elif len(path.rstrip('/')) > len(base_path) + 5:
                    is_gallery_like = True

            # Links with thumbnail and longer path than base (catch-all for thumb grids)
            if not is_gallery_like and has_thumb and len(path) > 10:
                # Skip very short paths (single segment like /teen/, /milf/)
                segments = [s for s in path.strip('/').split('/') if s]
                if len(segments) >= 2 or (len(segments) == 1 and len(segments[0]) > 20):
                    is_gallery_like = True

            if is_gallery_like:
                seen_urls.add(full_url)
                gallery_links.append(full_url)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(gallery_links))

    def _is_excluded_listing_link(self, url: str) -> bool:
        """Check if a link should be excluded from gallery listing"""
        path = urlparse(url).path.lower()

        excluded_patterns = [
            r'^/?$',  # Root
            r'[?&]page=',
            r'[?&]sort=',
            r'[?&]filter=',
            r'/page/\d+/?$',
            r'/tag/[^/]+/?$',
            r'/tags/[^/]+/?$',
            r'/category/[^/]+/?$',
            r'/categories/?$',
            r'/channels/?$',
            r'/pornstars/?$',
            r'/pornstar/[^/]+/?$',
            r'/models/?$',
            r'/search',
            r'/login',
            r'/register',
            r'/dmca',
            r'/privacy',
            r'/terms',
            r'/contact',
            r'/about',
            r'/sitemap',
        ]

        for pattern in excluded_patterns:
            if re.search(pattern, url) or re.search(pattern, path):
                return True

        return False

    async def _scroll_page(self, page, max_scrolls: int = 15):
        """Scroll page to load lazy-loaded / infinite scroll content.

        Scrolls multiple rounds, detecting when new content loads.
        Stops when no new content appears or max_scrolls reached.
        """
        try:
            prev_height = 0
            no_change_count = 0

            for i in range(max_scrolls):
                # Scroll to bottom
                current_height = await page.evaluate("document.body.scrollHeight")
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)  # Wait for new content to load

                # Check if new content appeared
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == current_height:
                    no_change_count += 1
                    if no_change_count >= 2:
                        break  # No new content after 2 tries
                else:
                    no_change_count = 0

                prev_height = new_height
        except Exception:
            pass

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
              help='Scraping mode: auto (try light first), light (requests only), browser (playwright only)')
def scrape(url: str, output: Optional[str], config: str, mode: str):
    """Scrape a single gallery from URL"""
    scraper = HybridScraper(config)
    output_dir = Path(output) if output else None
    asyncio.run(scraper.scrape_gallery(url, output_dir, mode))


@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--config', '-c', default='config.yaml', help='Config file path')
@click.option('--mode', '-m', type=click.Choice(['auto', 'light', 'browser']), default='auto',
              help='Scraping mode: auto (try light first), light (requests only), browser (playwright only)')
def batch(file: str, config: str, mode: str):
    """Scrape multiple galleries from a file (one URL per line)"""
    with open(file, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    scraper = HybridScraper(config)
    asyncio.run(scraper.scrape_multiple(urls, mode))


if __name__ == '__main__':
    cli()
