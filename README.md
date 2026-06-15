# AI News Alert — WhatsApp Bot

Sends AI news and new AI tool launches straight to your WhatsApp, in near real-time.
It polls multiple sources every few minutes, filters for AI relevance, summarizes each
item with an LLM (Groq / Llama 3.3), and delivers a clean message via Twilio WhatsApp.

## Features

- **Real-time** — polls every 15 min (configurable) and sends new items as they appear
- **Tool vs News** — detects and labels new AI tool/product launches separately from general news
- **Smart summaries** — 2–3 sentence digest per article via Groq (free tier)
- **No duplicates** — tracks seen articles, seeds existing news on first run so you aren't flooded
- **Many sources** — TechCrunch, VentureBeat, The Verge, Wired, HuggingFace, OpenAI, DeepMind,
  BAIR, Ars Technica, Product Hunt, Hacker News, and NewsAPI

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure credentials** — copy the template and fill in your keys:
   ```bash
   cp .env.example .env
   ```
   | Variable | Where to get it |
   |---|---|
   | `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | [console.twilio.com](https://console.twilio.com) |
   | `TWILIO_WHATSAPP_TO` | your number, e.g. `whatsapp:+91XXXXXXXXXX` |
   | `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) (free) |
   | `NEWS_API_KEY` | [newsapi.org](https://newsapi.org) (optional, free) |

   For Twilio, join the WhatsApp **sandbox** (Messaging → Try it out) by sending the
   `join <code>` message to the sandbox number.

3. **Run**
   ```bash
   python main.py
   ```

## Deploy on Railway

1. Push this repo to GitHub.
2. On [railway.app](https://railway.app): **New Project → Deploy from GitHub**, pick this repo.
3. Add every variable from `.env.example` in the Railway **Variables** tab
   (do **not** commit your real `.env`).
4. Railway uses `railway.toml` to run `python main.py` as a 24/7 worker.

## Project layout

| File | Purpose |
|---|---|
| `main.py` | Poll loop, orchestration |
| `news_fetcher.py` | RSS + Hacker News + NewsAPI fetching |
| `summarizer.py` | Keyword pre-filter + Groq summary & tool/news classification |
| `whatsapp_sender.py` | Twilio message formatting + send |
| `tracker.py` | Dedup of already-seen articles |
| `config.py` | Loads env vars |

## Notes

- Never commit `.env` — it holds your secrets and is already gitignored.
- Groq free tier is generous (thousands of requests/day); if a summary call fails,
  the bot falls back to the article's own description.
