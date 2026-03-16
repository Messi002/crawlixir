"""Core scraper - turns URLs into clean text, markdown, or HTML."""

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import urljoin, urlparse


class Scraper:
    """Fetches a URL and returns the content in a usable format."""

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    STRIP_TAGS = ["script", "style", "nav", "footer", "header", "aside", "noscript"]

    def __init__(self, headers=None, timeout=30, strip_tags=None):
        self.headers = headers or self.DEFAULT_HEADERS
        self.timeout = timeout
        self.strip_tags = strip_tags or self.STRIP_TAGS

    def fetch(self, url):
        """Fetch raw HTML from a URL. Falls back to Playwright if the site blocks requests."""
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 403:
                return self._fetch_with_browser(url)
            raise

    def _fetch_with_browser(self, url):
        """Use a headless browser when a site blocks plain HTTP requests."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                "This site blocked the request (403 Forbidden). "
                "Install Playwright to scrape it with a real browser:\n"
                "  pip install playwright && playwright install chromium"
            )

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)
            html = page.content()
            browser.close()
            return html

    def _clean_soup(self, html):
        """Parse HTML and remove unwanted tags."""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(self.strip_tags):
            tag.decompose()
        return soup

    def scrape(self, url, fmt="markdown"):
        """
        Fetch a URL and return its content.

        fmt can be 'markdown', 'text', 'html', or 'links'.
        Returns a dict with 'content', 'metadata', and 'links'.
        """
        html = self.fetch(url)
        soup = self._clean_soup(html)

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag["content"]

        if fmt == "markdown":
            content = md(str(soup.body or soup), strip=self.strip_tags)
        elif fmt == "text":
            content = soup.get_text(separator="\n", strip=True)
        elif fmt == "html":
            content = str(soup.body or soup)
        elif fmt == "links":
            content = self.extract_links(soup, url)
        else:
            raise ValueError(f"Unknown format: {fmt}. Use 'markdown', 'text', 'html', or 'links'.")

        links = self.extract_links(soup, url)

        return {
            "content": content,
            "metadata": {
                "title": title,
                "description": meta_desc,
                "source_url": url,
            },
            "links": links,
        }

    def extract_links(self, soup, base_url):
        """Extract all links from a page."""
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            absolute = urljoin(base_url, href)
            text = a.get_text(strip=True)
            links.append({"url": absolute, "text": text})
        return links

    def scrape_multiple(self, urls, fmt="markdown"):
        """Scrape multiple URLs and return results."""
        results = []
        for url in urls:
            try:
                result = self.scrape(url, fmt=fmt)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e), "source_url": url})
        return results
