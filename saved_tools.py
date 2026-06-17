"""
Searchable index of tools the bot has surfaced, so you can later ask
"web scraping" over WhatsApp and get back everything saved under it.

Stored as saved_tools.json via the storage backend (a GitHub Gist in
production, local file otherwise) so it survives Render restarts. Shape:

    { "web-scraping": [ {title, url, summary, source, saved_at}, ... ], ... }

Tools are deduped by URL across all categories.
"""

import re
import logging
from datetime import datetime, timezone

import storage
import categorize

log = logging.getLogger(__name__)

SAVED_FILE = "saved_tools.json"
MAX_PER_CATEGORY = 60  # keep the gist small; oldest drop off first


def _load() -> dict:
    data = storage.read_json(SAVED_FILE, {})
    return data if isinstance(data, dict) else {}


def _all_urls(data: dict) -> set[str]:
    return {it.get("url") for items in data.values() for it in items}


def save(item: dict) -> bool:
    """
    Persist a surfaced tool under its category. `item` needs at least url+title;
    `category` is used if present, otherwise inferred. Returns True if newly
    saved, False if it was a duplicate or unusable.
    """
    url = (item.get("url") or "").strip()
    title = (item.get("title") or "").strip()
    if not url or not title:
        return False

    data = _load()
    if url in _all_urls(data):
        return False  # already indexed

    category = item.get("category") or ""
    if not categorize.is_category(category):
        category = categorize.infer_category(f"{title} {item.get('summary', '')}")

    entry = {
        "title": title,
        "url": url,
        "summary": (item.get("summary") or "").strip(),
        "source": (item.get("source") or "").strip(),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    bucket = data.setdefault(category, [])
    bucket.append(entry)
    if len(bucket) > MAX_PER_CATEGORY:
        del bucket[: len(bucket) - MAX_PER_CATEGORY]

    storage.write_json(SAVED_FILE, data)
    log.info(f"Saved tool under '{category}': {title[:60]}")
    return True


def save_manual(category_text: str, title: str, url: str, summary: str = "") -> str:
    """Add a tool by hand (from the 'save' command). Returns the category used."""
    slug = categorize.normalize(category_text)
    if not categorize.is_category(slug):
        slug = categorize.infer_category(f"{category_text} {title} {summary}")
    save({"title": title, "url": url, "summary": summary,
          "source": "added manually", "category": slug})
    return slug


def categories() -> list[tuple[str, int]]:
    """[(category, count), ...] sorted by count desc, for the 'categories' command."""
    data = _load()
    return sorted(((c, len(items)) for c, items in data.items() if items),
                  key=lambda x: (-x[1], x[0]))


def search(query: str) -> list[dict]:
    """
    Find saved tools matching a free-text query. Combines an exact/loose
    category match with a keyword scan over title+summary, ranked by relevance.
    """
    data = _load()
    if not data:
        return []

    q = query.strip().lower()
    qslug = categorize.normalize(q)
    terms = [t for t in re.split(r"\s+", q) if len(t) > 2]

    scored: dict[str, tuple[int, dict]] = {}
    for cat, items in data.items():
        cat_match = qslug and (qslug == cat or qslug in cat or cat in qslug)
        for it in items:
            hay = f"{it.get('title','')} {it.get('summary','')} {cat}".lower()
            score = sum(1 for t in terms if t in hay)
            if cat_match:
                score += 5
            if score <= 0:
                continue
            url = it.get("url", "")
            if url not in scored or score > scored[url][0]:
                scored[url] = (score, it)

    ranked = sorted(scored.values(), key=lambda x: -x[0])
    return [it for _, it in ranked]
