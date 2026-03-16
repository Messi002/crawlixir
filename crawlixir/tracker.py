"""Watches pages for changes between visits."""

import json
import os
import hashlib
import difflib
from datetime import datetime
from .scraper import Scraper


class Tracker:
    """Saves snapshots of pages and diffs them on the next visit."""

    def __init__(self, storage_dir=".crawlixir_tracking", scraper=None):
        self.storage_dir = storage_dir
        self.scraper = scraper or Scraper()
        os.makedirs(storage_dir, exist_ok=True)

    def _url_hash(self, url):
        return hashlib.md5(url.encode()).hexdigest()

    def _snapshot_path(self, url):
        return os.path.join(self.storage_dir, f"{self._url_hash(url)}.json")

    def check(self, url):
        """
        Scrape the URL and compare it to the last saved snapshot.
        Returns a dict with 'changed' (bool), 'diff', and 'message'.
        """
        result = self.scraper.scrape(url, fmt="text")
        new_content = result["content"]
        snapshot_path = self._snapshot_path(url)

        old_content = None
        if os.path.exists(snapshot_path):
            with open(snapshot_path, "r") as f:
                data = json.load(f)
                old_content = data.get("content", "")

        # Save new snapshot
        with open(snapshot_path, "w") as f:
            json.dump({
                "url": url,
                "content": new_content,
                "timestamp": datetime.now().isoformat(),
            }, f)

        if old_content is None:
            return {"changed": False, "diff": "", "message": "First snapshot saved."}

        if old_content == new_content:
            return {"changed": False, "diff": "", "message": "No changes detected."}

        diff = "\n".join(difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            fromfile="previous",
            tofile="current",
            lineterm="",
        ))
        return {"changed": True, "diff": diff, "message": "Changes detected."}
