import json
import os
from datetime import datetime, timedelta

TRACKER_FILE = "seen_articles.json"


class ArticleTracker:
    def __init__(self):
        self._seen: dict[str, str] = {}

    def load(self):
        if os.path.exists(TRACKER_FILE):
            with open(TRACKER_FILE, "r") as f:
                self._seen = json.load(f)
        return self

    def is_seen(self, url: str) -> bool:
        return url in self._seen

    def mark(self, url: str):
        self._seen[url] = datetime.utcnow().isoformat()

    def mark_all(self, urls: list[str]):
        for url in urls:
            self.mark(url)

    def save(self):
        cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
        self._seen = {k: v for k, v in self._seen.items() if v > cutoff}
        with open(TRACKER_FILE, "w") as f:
            json.dump(self._seen, f, indent=2)
