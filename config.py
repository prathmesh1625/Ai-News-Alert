import os
from dotenv import load_dotenv

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
TWILIO_WHATSAPP_TO = os.getenv("TWILIO_WHATSAPP_TO")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES", "15"))

# How far back to look for articles each run. Must comfortably exceed the worst
# real gap between runs — GitHub Actions often throttles cron to 2-3h — or fresh
# news published between runs gets filtered out before the tracker ever sees it.
# The tracker dedups, so a wide window only re-checks; it never re-sends.
LOOKBACK_MINUTES = int(os.getenv("LOOKBACK_MINUTES", "360"))

# ── Twilio free-tier budget ─────────────────────────────────────────────────
# Hard cap on WhatsApp messages per UTC day (protects the free trial credit).
MAX_SENDS_PER_DAY = int(os.getenv("MAX_SENDS_PER_DAY", "12"))
# Don't fire more than this many news items in a single run (avoids a burst
# eating the whole daily cap at once).
MAX_NEWS_PER_RUN = int(os.getenv("MAX_NEWS_PER_RUN", "6"))
# Minimum hours between evergreen (existing-tool / tip) fallback sends.
FALLBACK_GAP_HOURS = float(os.getenv("FALLBACK_GAP_HOURS", "4"))
