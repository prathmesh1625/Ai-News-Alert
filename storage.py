"""
Tiny JSON persistence with a pluggable backend.

Render's free tier has an *ephemeral* disk: every restart/redeploy wipes local
files, so the bot forgets what it already sent and re-sends duplicates. To make
state survive restarts we optionally persist to a private GitHub Gist (free,
no extra service to run).

Enable it by setting two env vars:
  • GIST_TOKEN — a GitHub token with the "gist" scope
  • GIST_ID    — the id of a (secret) gist used as the store

If either is missing we transparently fall back to local files, so local dev
and GitHub Actions keep working exactly as before.
"""

import json
import os
import logging
import urllib.request
import urllib.error

log = logging.getLogger(__name__)

GIST_ID = os.getenv("GIST_ID", "").strip()
GIST_TOKEN = os.getenv("GIST_TOKEN", "").strip()
_USE_GIST = bool(GIST_ID and GIST_TOKEN)

# Cache the gist's files for the lifetime of a single read/write burst so we
# don't GET the whole gist once per file.
_gist_cache: dict | None = None


def using_gist() -> bool:
    return _USE_GIST


def _gist_api(method: str, payload: dict | None = None) -> dict:
    url = f"https://api.github.com/gists/{GIST_ID}"
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {GIST_TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "ai-news-alert")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def _load_gist_files() -> dict:
    global _gist_cache
    if _gist_cache is None:
        gist = _gist_api("GET")
        _gist_cache = gist.get("files", {}) or {}
    return _gist_cache


def read_json(name: str, default):
    """Read a JSON file from the gist (if enabled) else the local disk."""
    if _USE_GIST:
        try:
            files = _load_gist_files()
            entry = files.get(name)
            if entry and entry.get("content"):
                return json.loads(entry["content"])
            return default
        except Exception as e:
            log.warning(f"Gist read failed for {name}: {e} — falling back to local file.")

    if os.path.exists(name):
        try:
            with open(name) as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Could not read local {name}: {e}")
    return default


def write_json(name: str, data) -> None:
    """Write a JSON file to the gist (if enabled) else the local disk."""
    content = json.dumps(data, indent=2)
    if _USE_GIST:
        try:
            _gist_api("PATCH", {"files": {name: {"content": content}}})
            # Keep the in-process cache consistent with what we just wrote.
            if _gist_cache is not None:
                _gist_cache[name] = {"content": content}
            return
        except Exception as e:
            log.warning(f"Gist write failed for {name}: {e} — writing local file instead.")

    with open(name, "w") as f:
        f.write(content)
