"""
Turns an incoming WhatsApp message into a reply. Pure text in, text out —
the web webhook handles delivery.

Supported:
  • <topic>                       → search saved tools (e.g. "web scraping")
  • categories / list / topics    → all categories with counts
  • save <topic> | <name> | <url> → add a tool by hand
  • help / hi / menu              → usage
"""

import saved_tools

MAX_RESULTS = 10
MAX_LEN = 1500  # stay well under WhatsApp's ~1600-char limit

_HELP = (
    "🤖 *AI Tools Assistant*\n\n"
    "• Text a topic to search your saved tools, e.g. *web scraping*, "
    "*data extraction*, *coding*, *agents*.\n"
    "• *categories* — list everything I've saved, by topic.\n"
    "• *save <topic> | <name> | <url>* — add a tool by hand.\n\n"
    "Tools I send you are saved automatically, so just ask whenever you need one."
)


def _truncate(text: str) -> str:
    return text if len(text) <= MAX_LEN else text[: MAX_LEN - 1].rstrip() + "…"


def _format_results(query: str, results: list[dict]) -> str:
    shown = results[:MAX_RESULTS]
    head = f"🔎 *{query.strip()}* — {len(results)} saved"
    lines = [head, ""]
    for i, it in enumerate(shown, 1):
        lines.append(f"{i}. *{it['title']}*\n   {it['url']}")
    if len(results) > MAX_RESULTS:
        lines.append(f"\n…and {len(results) - MAX_RESULTS} more — add a word to narrow it down.")
    return _truncate("\n".join(lines))


def _handle_save(text: str) -> str:
    parts = [p.strip() for p in text[len("save"):].split("|")]
    if len(parts) < 3 or not parts[1] or not parts[2]:
        return ("To add a tool, use:\n*save <topic> | <name> | <url>*\n"
                "e.g. save web scraping | Firecrawl | https://firecrawl.dev")
    topic, name, url = parts[0], parts[1], parts[2]
    summary = parts[3] if len(parts) > 3 else ""
    used = saved_tools.save_manual(topic, name, url, summary)
    return f"✅ Saved *{name}* under *{used}*."


def handle(body: str) -> str:
    text = (body or "").strip()
    low = text.lower()

    if not text or low in ("help", "hi", "hello", "hey", "start", "menu", "?"):
        return _HELP

    if low in ("categories", "category", "list", "topics", "all", "saved"):
        cats = saved_tools.categories()
        if not cats:
            return "Nothing saved yet — tools will show up here as I find them."
        lines = ["🗂 *Saved categories*", ""]
        lines += [f"• {c} ({n})" for c, n in cats]
        lines.append("\nText a topic name to see the tools in it.")
        return _truncate("\n".join(lines))

    if low.startswith("save "):
        return _handle_save(text)

    results = saved_tools.search(text)
    if not results:
        return (f'No saved tools match "{text}". '
                'Text *categories* to see what I\'ve saved so far.')
    return _format_results(text, results)
