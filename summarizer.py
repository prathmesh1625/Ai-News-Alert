import logging
from groq import Groq
from config import GROQ_API_KEY

log = logging.getLogger(__name__)
client = Groq(api_key=GROQ_API_KEY)

MODEL = "llama-3.3-70b-versatile"

_AI_KEYWORDS = {
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "llm", "gpt", "claude", "gemini", "openai", "anthropic", "hugging face",
    "neural network", "chatbot", "generative", "diffusion", "transformer",
    "copilot", "midjourney", "stable diffusion", "large language model",
    "foundation model", "nvidia", "deepmind", "mistral", "llama", "groq",
    "perplexity", "sora", "dall-e", "computer vision", "nlp",
    # tool / update signals
    "ai tool", "ai app", "ai assistant", "ai agent", "launches", "released",
    "new model", "open source", "open-source", "plugin", "api", "feature",
    "update", "version", "available now",
}


def quick_filter(article: dict) -> bool:
    """Cheap keyword pre-filter before calling Groq (saves API quota)."""
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    return any(kw in text for kw in _AI_KEYWORDS)


_SYSTEM_PROMPT = (
    "You are a strict AI-news curator for a busy professional who wants to USE "
    "AI to make their work easier. Only surface high-value items. "
    "Respond in EXACTLY this format:\n"
    "DECISION: <KEEP|SKIP>\n"
    "TYPE: <tool|update|news>\n"
    "SUMMARY: <2-3 sentences: what it is and why it's useful>\n\n"
    "KEEP only if the article is one of these AND is genuinely significant:\n"
    "  • tool   = a NEW AI tool, app, product, or model people can actually use\n"
    "  • update = a meaningful new version, feature, or capability of an existing AI product/model\n"
    "  • news   = important AI news that affects how people work or what's possible\n\n"
    "SKIP (reply DECISION: SKIP) for low-value noise, even if AI-related:\n"
    "  • funding rounds, valuations, IPOs, stock/share price\n"
    "  • layoffs, hiring, executive/personnel moves\n"
    "  • opinion pieces, predictions, think-pieces, 'could/might' speculation\n"
    "  • lawsuits, drama, or politics with no product/tool impact\n"
    "  • vague roundups, listicles, or anything not about a concrete tool/update/development\n"
    "  • anything NOT about AI/ML at all\n\n"
    "Be selective — when in doubt, SKIP."
)


def summarize(article: dict) -> dict | None:
    """
    Returns {"summary": str, "type": "tool"|"update"|"news"} for items worth
    sending, or None to skip (low value / not AI / error with no usable text).
    """
    title = article.get("title", "")
    description = (article.get("summary", "") or "")[:800]

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"Title: {title}\n\nDescription: {description}"},
            ],
            max_tokens=200,
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()

        decision = "KEEP"
        article_type = "news"
        summary = ""

        for line in raw.splitlines():
            line = line.strip()
            if line.upper().startswith("DECISION:"):
                decision = line.split(":", 1)[1].strip().upper()
            elif line.upper().startswith("TYPE:"):
                val = line.split(":", 1)[1].strip().lower()
                if val in ("tool", "update", "news"):
                    article_type = val
            elif line.upper().startswith("SUMMARY:"):
                summary = line.split(":", 1)[1].strip()

        if decision != "KEEP" or not summary:
            return None

        return {"summary": summary, "type": article_type}

    except Exception as e:
        log.error(f"Groq error: {e}")
        # On a transient API error, don't lose the item — send raw as news.
        raw = article.get("summary", "")
        if not raw:
            return None
        return {"summary": raw[:300], "type": "news"}
