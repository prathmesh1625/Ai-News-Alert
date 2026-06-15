import re
import time
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from config import NEWS_API_KEY, POLL_INTERVAL_MINUTES

log = logging.getLogger(__name__)

RSS_FEEDS = [
    # ── AI News ─────────────────────────────────────────────────────────
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://www.wired.com/feed/tag/ai/latest/rss",
    "https://huggingface.co/blog/feed.xml",
    "https://bair.berkeley.edu/blog/feed.xml",
    "https://openai.com/news/rss.xml",
    "https://www.deepmind.com/blog/rss.xml",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    # ── AI Tools & Launches ──────────────────────────────────────────────
    "https://www.producthunt.com/feed?category=artificial-intelligence",
]

_NS = {
    "atom":    "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc":      "http://purl.org/dc/elements/1.1/",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; AI-News-Alert-Bot/1.0)"}


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _parse_date(text: str | None) -> datetime | None:
    if not text:
        return None
    text = text.strip()
    try:
        return parsedate_to_datetime(text).astimezone(timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text[:19], fmt[:len(text[:19])])
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def _text(el, *tags) -> str:
    for tag in tags:
        child = el.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        for ns_uri in _NS.values():
            child = el.find(f"{{{ns_uri}}}{tag}")
            if child is not None and child.text:
                return child.text.strip()
    return ""


def _parse_feed_xml(xml_bytes: bytes, feed_url: str) -> list[dict]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        log.warning(f"XML parse error [{feed_url}]: {e}")
        return []

    articles = []
    tag = root.tag.lower()

    if "feed" in tag:
        ns = "http://www.w3.org/2005/Atom"
        source_name = _text(root, "title", f"{{{ns}}}title") or feed_url
        entries = root.findall(f"{{{ns}}}entry") or root.findall("entry")
        for entry in entries:
            title = _strip_html(_text(entry, "title", f"{{{ns}}}title"))
            summary = _strip_html(
                _text(entry, "summary", "content", f"{{{ns}}}summary", f"{{{ns}}}content")
            )
            published_str = _text(entry, "published", "updated", f"{{{ns}}}published", f"{{{ns}}}updated")
            link_el = entry.find(f"{{{ns}}}link") or entry.find("link")
            url = link_el.get("href", "") if link_el is not None else ""
            if url:
                articles.append({
                    "url": url, "title": title, "summary": summary,
                    "source": source_name, "published": _parse_date(published_str),
                })
    else:
        channel = root.find("channel") or root
        source_name = _text(channel, "title") or feed_url
        for item in channel.findall(".//item"):
            title = _strip_html(_text(item, "title"))
            summary = _strip_html(
                _text(item, "description", "summary",
                      f"{{{_NS['content']}}}encoded")
            )
            url = _text(item, "link", "guid")
            published_str = _text(item, "pubDate", f"{{{_NS['dc']}}}date")
            if url:
                articles.append({
                    "url": url, "title": title, "summary": summary[:600],
                    "source": source_name, "published": _parse_date(published_str),
                })

    return articles


def fetch_rss_articles(lookback_minutes: int) -> list[dict]:
    """
    Fetches RSS items published within `lookback_minutes`.
    Tracker handles dedup — this window just prevents pulling the full archive.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
    articles = []
    for feed_url in RSS_FEEDS:
        try:
            resp = requests.get(feed_url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            parsed = _parse_feed_xml(resp.content, feed_url)
            count = 0
            for a in parsed:
                pub = a.pop("published")
                # Include articles with no date (can't exclude them safely)
                if pub and pub < cutoff:
                    continue
                a["published"] = pub.isoformat() if pub else None
                articles.append(a)
                count += 1
            log.debug(f"  RSS [{feed_url.split('/')[2]}]: {count} items in window")
        except Exception as e:
            log.warning(f"RSS error [{feed_url}]: {e}")
    return articles


def fetch_hackernews_articles(lookback_minutes: int) -> list[dict]:
    """HackerNews Algolia — no auth, very reliable."""
    cutoff = int((datetime.utcnow() - timedelta(minutes=lookback_minutes)).timestamp())
    try:
        resp = requests.get(
            "https://hn.algolia.com/api/v1/search_by_date",
            params={
                "tags": "story",
                "query": "AI OR artificial intelligence OR LLM OR GPT OR machine learning",
                "numericFilters": f"created_at_i>{cutoff}",
                "hitsPerPage": 20,
            },
            timeout=10,
        )
        data = resp.json()
        articles = []
        for hit in data.get("hits", []):
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            articles.append({
                "url": url,
                "title": hit.get("title", ""),
                "summary": "",
                "source": "Hacker News",
                "published": hit.get("created_at"),
            })
        log.debug(f"  HackerNews: {len(articles)} items")
        return articles
    except Exception as e:
        log.warning(f"HackerNews error: {e}")
        return []


def fetch_newsapi_articles(lookback_minutes: int) -> list[dict]:
    if not NEWS_API_KEY:
        return []
    from_time = (datetime.utcnow() - timedelta(minutes=lookback_minutes)).strftime(
        "%Y-%m-%dT%H:%M:%S"
    )
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": (
                    "artificial intelligence OR AI model OR machine learning "
                    "OR LLM OR GPT OR Claude OR Gemini OR generative AI "
                    "OR AI tool OR AI app OR AI startup"
                ),
                "from": from_time,
                "sortBy": "publishedAt",
                "language": "en",
                "apiKey": NEWS_API_KEY,
                "pageSize": 20,
            },
            timeout=10,
        )
        data = resp.json()
        articles = []
        for a in data.get("articles", []):
            url = a.get("url", "")
            if not url or url == "https://removed.com":
                continue
            articles.append({
                "url": url,
                "title": a.get("title", ""),
                "summary": a.get("description", ""),
                "source": a.get("source", {}).get("name", ""),
                "published": a.get("publishedAt"),
            })
        log.debug(f"  NewsAPI: {len(articles)} items")
        return articles
    except Exception as e:
        log.warning(f"NewsAPI error: {e}")
        return []


def fetch_all(lookback_minutes: int | None = None) -> list[dict]:
    """
    Uses a 2× poll interval window so articles at the boundary of two poll
    cycles are never missed. Tracker handles dedup so overlap is harmless.
    """
    window = lookback_minutes if lookback_minutes is not None else max(POLL_INTERVAL_MINUTES * 2, 60)

    rss = fetch_rss_articles(window)
    api = fetch_newsapi_articles(window)
    hn  = fetch_hackernews_articles(window)

    seen_urls: set[str] = set()
    combined = []
    for article in rss + api + hn:
        url = article.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            combined.append(article)

    return combined
