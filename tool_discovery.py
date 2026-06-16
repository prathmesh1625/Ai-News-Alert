"""
Priority 2 — live discovery of *lesser-known* but genuinely useful AI/ML tools.

No predefined tool list. Each run searches GitHub for AI/ML projects, throws out
the household names (Ollama, LangChain, Stable Diffusion, …), and asks Groq to
pick the one hidden gem worth knowing and write a short "why it's useful" blurb.

The star window is deliberate: a floor filters out abandoned toys/demos, and a
ceiling filters out the megastar tools you already know — biasing toward "tools
someone probably hasn't heard of yet" (the Unsloth-style finds).
"""

import re
import json
import random
import logging
import requests

from groq import Groq
from config import GROQ_API_KEY, GITHUB_TOKEN

log = logging.getLogger(__name__)
_client = Groq(api_key=GROQ_API_KEY)
MODEL = "llama-3.3-70b-versatile"

# Rotated each run so the channel sees variety over time.
_QUERIES = [
    "topic:llm stars:200..18000 pushed:>2025-06-01",
    "topic:ai-agent stars:150..18000 pushed:>2025-06-01",
    "topic:ai-tools stars:100..18000 pushed:>2025-06-01",
    "topic:rag stars:100..15000 pushed:>2025-06-01",
    "topic:llmops stars:80..15000 pushed:>2025-06-01",
    "topic:ai-assistant stars:100..15000 pushed:>2025-06-01",
    "topic:machine-learning-tools stars:80..15000 pushed:>2025-06-01",
    "topic:generative-ai stars:200..18000 pushed:>2025-06-01",
    "topic:fine-tuning stars:80..15000",
    "topic:vector-database stars:150..18000",
]

# Names everyone already knows — never resurface these as "lesser-known".
_TOO_FAMOUS = {
    "ollama", "langchain", "langgraph", "llama", "llama.cpp", "transformers",
    "stable-diffusion", "stable-diffusion-webui", "comfyui", "whisper",
    "faster-whisper", "auto-gpt", "autogpt", "privategpt", "gpt4all",
    "unsloth", "vllm", "open-webui", "text-generation-webui", "fooocus",
    "langflow", "flowise", "dify", "n8n", "supabase", "chroma", "milvus",
    "llamaindex", "llama_index", "haystack", "litellm", "ragflow", "anythingllm",
    "openai-cookbook", "transformers.js", " comfyui",
}

HEADERS = {
    "User-Agent": "AI-News-Alert-Bot/1.0",
    "Accept": "application/vnd.github+json",
}

_PICK_PROMPT = (
    "You help a busy professional discover GENUINELY USEFUL AI/ML tools they "
    "probably DON'T already know about.\n"
    "You'll get a numbered list of open-source projects (name, stars, description, "
    "topics, url). Pick exactly ONE that is:\n"
    "  • a practical tool/app/library someone can actually USE to get work done,\n"
    "  • credible and genuinely useful (not a toy, demo, tutorial, course, awesome-list, or paper),\n"
    "  • NOT a household name — exclude anything most developers already know "
    "(Ollama, LangChain, AutoGPT, Stable Diffusion, vLLM, etc.).\n"
    "Prefer the hidden gem over the obvious popular one.\n"
    "Respond with ONLY a JSON object, no other text:\n"
    '{"index": <number from the list>, "title": "<Tool name — short hook>", '
    '"summary": "<2-3 sentences: what it does and why it is useful>"}'
)


def _github_candidates(limit: int = 25) -> list[dict]:
    query = random.choice(_QUERIES)
    headers = dict(HEADERS)
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    try:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            params={
                "q": query,
                "sort": random.choice(["stars", "updated"]),
                "order": "desc",
                "per_page": limit,
            },
            headers=headers,
            timeout=12,
        )
        resp.raise_for_status()
        items = []
        for repo in resp.json().get("items", []):
            name = (repo.get("name") or "").lower()
            if name in _TOO_FAMOUS:
                continue
            items.append({
                "name": repo.get("full_name", ""),
                "url": repo.get("html_url", ""),
                "description": (repo.get("description") or "")[:300],
                "stars": repo.get("stargazers_count", 0),
                "topics": (repo.get("topics") or [])[:6],
            })
        log.debug(f"  GitHub discovery [{query}]: {len(items)} candidates")
        return items
    except Exception as e:
        log.warning(f"GitHub discovery error: {e}")
        return []


def _extract_json(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def discover_tool(is_seen) -> dict | None:
    """
    Returns an evergreen-style item for one freshly-discovered, lesser-known
    AI tool, or None if nothing usable was found this run. `is_seen(url)` lets
    the caller's tracker skip tools already sent in the last week.
    """
    candidates = [c for c in _github_candidates() if c["url"] and not is_seen(c["url"])]
    if not candidates:
        log.info("Tool discovery: no fresh candidates this run.")
        return None

    listing = "\n".join(
        f"{i}. {c['name']} ({c['stars']}★) — {c['description']} "
        f"[topics: {', '.join(c['topics'])}] {c['url']}"
        for i, c in enumerate(candidates)
    )

    try:
        resp = _client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": _PICK_PROMPT},
                {"role": "user", "content": f"Candidates:\n{listing}"},
            ],
            max_tokens=300,
            temperature=0.4,
        )
        data = _extract_json(resp.choices[0].message.content.strip())
        if data and 0 <= int(data.get("index", -1)) < len(candidates):
            chosen = candidates[int(data["index"])]
            summary = (data.get("summary") or chosen["description"]).strip()
            title = (data.get("title") or chosen["name"]).strip()
            return {
                "url": chosen["url"],
                "title": title,
                "summary": summary,
                "source": f"GitHub · {chosen['stars']}★",
                "type": "evergreen_tool",
            }
        log.warning("Tool discovery: Groq returned no usable pick — using fallback candidate.")
    except Exception as e:
        log.warning(f"Tool discovery Groq error: {e}")

    # Fallback: the least-known credible candidate, described by its own README blurb.
    chosen = min(
        (c for c in candidates if c["description"]),
        key=lambda c: c["stars"],
        default=None,
    )
    if not chosen:
        return None
    return {
        "url": chosen["url"],
        "title": chosen["name"],
        "summary": chosen["description"],
        "source": f"GitHub · {chosen['stars']}★",
        "type": "evergreen_tool",
    }
