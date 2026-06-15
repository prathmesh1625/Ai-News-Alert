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
    # tool-launch signals
    "ai tool", "ai app", "ai assistant", "ai agent", "launches", "released",
    "new model", "open source", "open-source", "plugin", "api release",
}


def quick_filter(article: dict) -> bool:
    """Keyword pre-filter before calling Groq (saves API quota)."""
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    return any(kw in text for kw in _AI_KEYWORDS)


def summarize(article: dict) -> dict | None:
    """
    Returns {"summary": str, "type": "tool"|"news"} or None if not AI-related.
    Uses llama-3.3-70b-versatile via Groq (free tier).
    """
    title = article.get("title", "")
    description = (article.get("summary", "") or "")[:800]

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an AI news curator. Analyze the article and respond in this exact format:\n"
                        "TYPE: <tool|news>\n"
                        "SUMMARY: <2-3 sentences>\n\n"
                        "TYPE rules:\n"
                        "- 'tool' = a new AI product, app, plugin, model, or API was launched/released/open-sourced\n"
                        "- 'news' = research, updates, policy, funding, general AI news\n\n"
                        "SUMMARY rules: be factual, explain what's new and why it matters.\n"
                        "If the article is NOT about AI/ML at all, reply with exactly: NOT_AI_NEWS"
                    ),
                },
                {
                    "role": "user",
                    "content": f"Title: {title}\n\nDescription: {description}",
                },
            ],
            max_tokens=180,
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()

        if raw == "NOT_AI_NEWS":
            return None

        article_type = "news"
        summary = raw

        for line in raw.splitlines():
            if line.startswith("TYPE:"):
                val = line.split(":", 1)[1].strip().lower()
                if val in ("tool", "news"):
                    article_type = val
            elif line.startswith("SUMMARY:"):
                summary = line.split(":", 1)[1].strip()

        return {"summary": summary, "type": article_type}

    except Exception as e:
        log.error(f"Groq error: {e}")
        raw = article.get("summary", "")
        if not raw:
            return None
        return {"summary": raw[:300], "type": "news"}
