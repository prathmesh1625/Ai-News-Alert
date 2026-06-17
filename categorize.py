"""
Fixed category vocabulary for the saved-tools index, plus a cheap keyword-based
classifier used when the summarizer didn't already assign one (e.g. tools found
by live discovery). A fixed list keeps the index from fragmenting into
"scraper" / "scraping" / "web-scrapers".

web-scraping and data-extraction come FIRST on purpose — those are the
categories the user most cares about, so ambiguous items lean that way.
"""

import re

CATEGORIES = [
    "web-scraping",
    "data-extraction",
    "image-gen",
    "video",
    "voice-audio",
    "coding",
    "agents",
    "llm-models",
    "rag-search",
    "data-analysis",
    "automation",
    "productivity",
    "design",
    "other",
]

# Checked in order; first category with a matching keyword wins.
_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("web-scraping", ["scrap", "crawl", "spider", "headless browser", "playwright",
                       "puppeteer", "selenium", "web data", "html parsing"]),
    ("data-extraction", ["extract", "parser", "parsing", " ocr", "pdf", "etl",
                          "structured data", "document ai", "table extraction", "screenshot to"]),
    ("image-gen", ["image generation", "text-to-image", "diffusion", "midjourney",
                   "dall-e", "dalle", "stable diffusion", "photo", "art generator", "upscal"]),
    ("video", ["video", "text-to-video", "animation", "sora", "runway", "lip sync"]),
    ("voice-audio", ["voice", "speech", "audio", "text-to-speech", "tts", "stt",
                     "transcription", "transcribe", "whisper", "music", "podcast"]),
    ("coding", ["code", "coding", "developer", "ide", "copilot", "programming",
                "debug", "code review", "autocomplete", "code generation"]),
    ("agents", ["agent", "autonomous", "multi-agent", "agentic", "workflow agent"]),
    ("llm-models", ["llm", "language model", "foundation model", "fine-tun", "fine tune",
                    "gpt", "llama", "mistral", "open-weight", "new model"]),
    ("rag-search", ["rag", "retrieval", "vector database", "vector search", "embedding",
                    "semantic search", "knowledge base"]),
    ("data-analysis", ["data analysis", "analytics", "dataframe", "visualization",
                        "dashboard", "spreadsheet", "sql"]),
    ("automation", ["automation", "automate", "n8n", "zapier", "workflow", "no-code", "rpa"]),
    ("productivity", ["productivity", "note-taking", "notes", "writing assistant",
                      "email", "calendar", "meeting", "summariz", "presentation"]),
    ("design", ["design", "ui ", "ux", "figma", "logo", "slide", "mockup", "wireframe"]),
]


def normalize(text: str) -> str:
    """'Web Scraping!' -> 'web-scraping' (matches a category slug)."""
    return re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")


def is_category(slug: str) -> bool:
    return slug in CATEGORIES


def infer_category(text: str) -> str:
    """Best-effort category from free text. Falls back to 'other'."""
    t = (text or "").lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(kw in t for kw in keywords):
            return category
    return "other"
