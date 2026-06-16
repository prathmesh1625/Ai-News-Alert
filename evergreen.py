"""
Evergreen fallback content — sent only when there's no fresh AI news, so the
channel always delivers something useful.

Priority (matches the user's wishlist):
  1) new AI news / tools   -> handled by news_fetcher + summarizer (not here)
  2) existing AI tools      -> EXISTING_TOOLS below   (type="evergreen_tool")
  3) tips about AI tools    -> TIPS below             (type="tip")

Dedup: each item's `url` is stored in the same tracker as news articles. The
tracker expires entries after 7 days, so the whole library recycles roughly
every week — you keep seeing useful tools/tips without manual upkeep.
"""

# ── 2) Existing tools worth knowing ─────────────────────────────────────────
EXISTING_TOOLS = [
    {
        "id": "unsloth",
        "title": "Unsloth — fine-tune an LLM in minutes on a free GPU",
        "summary": "Open-source library that fine-tunes Llama, Mistral, Gemma and Qwen ~2× faster using up to 70% less VRAM. The free Colab/Kaggle notebooks let you train a model in roughly 10-15 minutes without owning a GPU.",
        "url": "https://github.com/unslothai/unsloth",
    },
    {
        "id": "ollama",
        "title": "Ollama — run powerful LLMs locally, offline & free",
        "summary": "One command (`ollama run llama3`) downloads and runs open models on your own machine — no API bills, full privacy. Great for drafting, coding help and experiments when you don't want to pay per token.",
        "url": "https://ollama.com",
    },
    {
        "id": "lmstudio",
        "title": "LM Studio — a friendly GUI for local AI models",
        "summary": "Point-and-click app to download and chat with open-source models on your laptop, with a built-in OpenAI-compatible server so your own scripts can call it for free.",
        "url": "https://lmstudio.ai",
    },
    {
        "id": "faster-whisper",
        "title": "faster-whisper — near-free, fast audio transcription",
        "summary": "A re-implementation of OpenAI Whisper that's up to 4× faster and lighter. Transcribe meetings, voice notes or videos locally with no per-minute API cost.",
        "url": "https://github.com/SYSTRAN/faster-whisper",
    },
    {
        "id": "perplexity",
        "title": "Perplexity — AI search that cites its sources",
        "summary": "Ask a question and get a sourced, up-to-date answer instead of a list of links. The free tier is plenty for daily research and fact-checking.",
        "url": "https://www.perplexity.ai",
    },
    {
        "id": "notebooklm",
        "title": "NotebookLM — turn your own docs into an AI study partner",
        "summary": "Upload PDFs, notes or links and ask grounded questions about them; it can even generate an audio 'podcast' summary. Free and great for learning or research.",
        "url": "https://notebooklm.google.com",
    },
    {
        "id": "groq-console",
        "title": "Groq — the fastest free LLM inference",
        "summary": "Runs Llama and other open models at hundreds of tokens/sec with a generous free API tier — ideal for chatbots, summarizers and the kind of automation this very bot uses.",
        "url": "https://console.groq.com",
    },
    {
        "id": "comfyui",
        "title": "ComfyUI — free, node-based AI image generation",
        "summary": "Build image pipelines visually and run Stable Diffusion / Flux locally for free. Steeper learning curve than web tools, but total control and no per-image cost.",
        "url": "https://github.com/comfyanonymous/ComfyUI",
    },
]

# ── 3) Practical tips about AI tools ────────────────────────────────────────
TIPS = [
    {
        "id": "tip-claude-code-tokens",
        "title": "Tip: make Claude Code use far fewer tokens",
        "summary": "Run /clear between unrelated tasks so old context stops being re-sent, keep a short CLAUDE.md instead of pasting big files, and let it read files on demand. Less context = cheaper, faster and sharper answers.",
        "url": "https://docs.anthropic.com/en/docs/claude-code/costs",
    },
    {
        "id": "tip-prompt-caching",
        "title": "Tip: cut API costs with prompt caching",
        "summary": "If you send the same long instructions or document on every request, enable prompt caching — repeated tokens get billed up to 90% cheaper. Huge savings for bots and RAG apps that reuse a big system prompt.",
        "url": "https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching",
    },
    {
        "id": "tip-batch-api",
        "title": "Tip: use the Batch API for 50% off",
        "summary": "For work that isn't time-sensitive (summaries, classification, bulk rewrites), send it via the Batch API and pay half price. Results come back within 24h — perfect for overnight jobs.",
        "url": "https://docs.anthropic.com/en/docs/build-with-claude/batch-processing",
    },
    {
        "id": "tip-right-size-model",
        "title": "Tip: don't use a big model for small jobs",
        "summary": "Route simple tasks (formatting, short summaries, keyword filtering) to a small/fast model and save the flagship model for hard reasoning. You'll cut cost and latency dramatically with no quality loss.",
        "url": "https://docs.anthropic.com/en/docs/about-claude/models",
    },
    {
        "id": "tip-examples-beat-instructions",
        "title": "Tip: show examples, don't just describe",
        "summary": "Two or three good input→output examples in your prompt steer an LLM far better than a paragraph of rules. 'Few-shot' prompting is the cheapest reliability upgrade you can make.",
        "url": "https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/multishot-prompting",
    },
    {
        "id": "tip-structured-output",
        "title": "Tip: ask for JSON to make AI output reliable",
        "summary": "When you'll parse the result in code, tell the model to reply in a strict JSON shape (and pre-fill the opening brace). You get clean, machine-readable output instead of fragile free text.",
        "url": "https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs",
    },
    {
        "id": "tip-rag-basics",
        "title": "Tip: stop an AI from making things up — give it the docs",
        "summary": "Instead of trusting the model's memory, retrieve the relevant text and paste it into the prompt ('RAG'). Answers become grounded in your actual data and hallucinations drop sharply.",
        "url": "https://www.anthropic.com/news/contextual-retrieval",
    },
]


def fallback_items() -> list[dict]:
    """
    All evergreen items in priority order: existing tools first, then tips.
    Each item is shaped like a news article so it flows through the same
    tracker + formatter (with a distinct `type`).
    """
    items: list[dict] = []
    for t in EXISTING_TOOLS:
        items.append({
            "url": t["url"],
            "title": t["title"],
            "summary": t["summary"],
            "source": "Tool worth knowing",
            "type": "evergreen_tool",
        })
    for t in TIPS:
        items.append({
            "url": t["url"],
            "title": t["title"],
            "summary": t["summary"],
            "source": "AI tip",
            "type": "tip",
        })
    return items


def pick_unseen(tracker) -> dict | None:
    """First evergreen item (tools before tips) not sent in the last 7 days."""
    for item in fallback_items():
        if not tracker.is_seen(item["url"]):
            return item
    return None
