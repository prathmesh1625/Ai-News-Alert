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


def all_tools() -> dict:
    """The whole {category: [tools]} map — used by the web dashboard."""
    return _load()


def is_saved(url: str) -> bool:
    """True if this tool was already sent/saved before (permanent, unlike the
    7-day tracker) — used to stop the same tool being surfaced again."""
    if not url:
        return False
    return url in _all_urls(_load())


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


def _matched_categories(qslug: str) -> list[str]:
    """Which known categories a query refers to (against the full vocabulary)."""
    if not qslug:
        return []
    if categorize.is_category(qslug):
        return [qslug]
    matched = []
    for cat in categorize.CATEGORIES:
        if cat == "other":  # only an exact 'other' counts, never a loose match
            continue
        if cat in qslug or qslug in cat:
            matched.append(cat)
    return matched


def search(query: str) -> list[dict]:
    """
    Find saved tools for a query. If the query names a known category, return
    ONLY that category's tools (even if empty) — so a tool never leaks into a
    topic it isn't filed under. Keyword search runs only for queries that don't
    name any category (e.g. a tool's name).
    """
    data = _load()
    if not data:
        return []

    cats = _matched_categories(categorize.normalize(query))
    if cats:
        results, seen = [], set()
        for cat in cats:
            for it in data.get(cat, []):
                if it.get("url") not in seen:
                    results.append(it)
                    seen.add(it.get("url"))
        return results

    terms = [t for t in re.split(r"\s+", query.strip().lower()) if len(t) > 2]
    if not terms:
        return []

    scored: dict[str, tuple[int, dict]] = {}
    for items in data.values():
        for it in items:
            hay = f"{it.get('title','')} {it.get('summary','')}".lower()
            score = sum(1 for t in terms if t in hay)
            if score <= 0:
                continue
            url = it.get("url", "")
            if url not in scored or score > scored[url][0]:
                scored[url] = (score, it)

    return [it for _, it in sorted(scored.values(), key=lambda x: -x[0])]
