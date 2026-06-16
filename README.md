# AI News Alert — WhatsApp Bot

Sends AI news and new AI tool launches straight to your WhatsApp, in near real-time.
It polls multiple sources every few minutes, filters for AI relevance, summarizes each
item with an LLM (Groq / Llama 3.3), and delivers a clean message via Twilio WhatsApp.

## Features

- **Real-time** — polls every 15 min (configurable) and sends new items as they appear
- **Survives cron throttling** — each run looks back `LOOKBACK_MINUTES` (default 6h), so even when
  GitHub Actions delays a scheduled run by hours, no fresh news is missed (the tracker dedups)
- **Never silent** — when there's no fresh news, it sends fallback value, in priority order:
  1. fresh AI news / tools, then 2. a **lesser-known existing tool discovered live** by
  searching GitHub (excludes household names — surfaces the Unsloth-style hidden gems), then
  3. a **practical AI tip** (e.g. cutting Claude Code token usage)
- **Twilio-budget aware** — hard daily message cap + spacing between fallbacks keep you on the free tier
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

## Deploy on Render (free)

GitHub Actions throttles free scheduled cron to ~2-5h between runs, which is too
slow for the 2-hour fallback cadence. Render's free **web service** can run the
poll loop continuously instead. (Render's worker/cron plans are paid; the free
web service is the only free option, so `web.py` wraps the loop in a tiny health
server.)

1. Push this repo to GitHub.
2. On [render.com](https://render.com): **New → Blueprint**, pick this repo. It
   reads `render.yaml` and creates a free web service running `python web.py`.
3. In the service's **Environment** tab, fill in the secret values
   (`TWILIO_*`, `GROQ_API_KEY`, `NEWS_API_KEY`) — they're marked `sync: false`
   so they're never committed.
4. **Keep it awake.** Free web services sleep after 15 min of no traffic. Create
   a free [UptimeRobot](https://uptimerobot.com) HTTP monitor that pings your
   Render URL every 5 minutes — this keeps the loop running 24/7 (≈730 hrs/mo,
   within the 750-hr free limit).

> ⚠️ Run **either** Render **or** the GitHub Actions schedule, not both — they
> keep separate state and would double-send. Once Render works, disable the
> Actions cron (comment out the `schedule:` block in the workflow).
>
> Render's free disk is ephemeral, so `seen_articles.json` / `bot_state.json`
> reset on each redeploy/restart. That's safe — a reset just re-seeds and sends
> nothing; only the daily budget counter resets.

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
| `tool_discovery.py` | Live discovery of lesser-known AI tools from GitHub + Groq (priority 2) |
| `evergreen.py` | Curated AI tips, the last-resort fallback (priority 3) |
| `state.py` | Persisted Twilio daily budget + fallback spacing (`bot_state.json`) |
| `tracker.py` | Dedup of already-seen articles (and fallback items; recycles weekly) |
| `config.py` | Loads env vars |

## Twilio free-tier tuning

| Variable | Default | Meaning |
|---|---|---|
| `MAX_SENDS_PER_DAY` | 12 | Hard cap on WhatsApp messages per UTC day |
| `MAX_NEWS_PER_RUN` | 6 | Max fresh-news items in one run (stops a burst eating the cap) |
| `FALLBACK_GAP_HOURS` | 4 | Min hours between existing-tool / tip fallbacks |
| `LOOKBACK_MINUTES` | 360 | How far back each run scans (set above your worst cron gap) |

> Twilio's WhatsApp **sandbox** session closes after 24h of no messages from you — if sends
> start failing, re-send the `join <code>` message to reopen it.

## Notes

- Never commit `.env` — it holds your secrets and is already gitignored.
- Groq free tier is generous (thousands of requests/day); if a summary call fails,
  the bot falls back to the article's own description.
