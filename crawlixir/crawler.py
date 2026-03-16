"""Recursive crawler with URL discovery."""

from urllib.parse import urljoin, urlparse
from .scraper import Scraper


class Crawler:
    """Walks through a website, page by page."""

    def __init__(self, scraper=None, max_depth=3, max_pages=100):
        self.scraper = scraper or Scraper()
        self.max_depth = max_depth
        self.max_pages = max_pages

    def map(self, url):
        """Discover all URLs on a website (single level)."""
        result = self.scraper.scrape(url, fmt="links")
        domain = urlparse(url).netloc
        internal = [l for l in result["links"] if urlparse(l["url"]).netloc == domain]
        external = [l for l in result["links"] if urlparse(l["url"]).netloc != domain]
        return {"internal": internal, "external": external, "total": len(result["links"])}

    def crawl(self, start_url, fmt="markdown"):
        """
        Follow links from start_url up to max_depth levels deep.
        Stops after max_pages pages. Returns a list of scraped results.
        """
        domain = urlparse(start_url).netloc
        visited = set()
        results = []
        queue = [(start_url, 0)]

        while queue and len(results) < self.max_pages:
            url, depth = queue.pop(0)

            if url in visited or depth > self.max_depth:
                continue
            visited.add(url)

            try:
                result = self.scraper.scrape(url, fmt=fmt)
                result["depth"] = depth
                results.append(result)

                if depth < self.max_depth:
                    for link in result.get("links", []):
                        link_url = link["url"].split("#")[0].split("?")[0]
                        if (urlparse(link_url).netloc == domain
                                and link_url not in visited):
                            queue.append((link_url, depth + 1))
            except Exception as e:
                results.append({"error": str(e), "source_url": url, "depth": depth})

        return results
