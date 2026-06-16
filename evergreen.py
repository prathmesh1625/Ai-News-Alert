"""
Priority 3 — practical AI tips, sent only when there's no fresh news AND tool
discovery found nothing new this run.

Tools (priority 2) are discovered live from the web in tool_discovery.py — there
is deliberately NO hardcoded tool list here. Tips, by contrast, are timeless
advice, so a small curated set is fine. The tracker expires entries after 7
days, so tips recycle roughly weekly.
"""

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


def pick_unseen_tip(tracker) -> dict | None:
    """First tip not sent in the last 7 days, shaped like an article for the formatter."""
    for tip in TIPS:
        if not tracker.is_seen(tip["url"]):
            return {
                "url": tip["url"],
                "title": tip["title"],
                "summary": tip["summary"],
                "source": "AI tip",
                "type": "tip",
            }
    return None
