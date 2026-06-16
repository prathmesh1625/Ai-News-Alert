from datetime import datetime, timedelta

import storage

TRACKER_FILE = "seen_articles.json"


class ArticleTracker:
    def __init__(self):
        self._seen: dict[str, str] = {}

    def load(self):
        self._seen = storage.read_json(TRACKER_FILE, {})
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
        storage.write_json(TRACKER_FILE, self._seen)
