"""Sends one real article to WhatsApp to verify the full pipeline."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from news_fetcher import fetch_all
from summarizer import quick_filter, summarize
from whatsapp_sender import send, format_message

print("Fetching articles (last 24 h)...")
articles = fetch_all(lookback_minutes=60 * 24)
print(f"Found {len(articles)} articles\n")

for article in articles:
    if not quick_filter(article):
        continue

    print(f"Article : {article['title'][:80]}")
    print(f"Source  : {article['source']}")

    result = summarize(article)
    if result is None:
        print("Groq says not AI-relevant, trying next...\n")
        continue

    print(f"Type    : {result['type']}")
    print(f"Summary : {result['summary'][:120]}")

    msg = format_message(article, result["summary"], result["type"])
    print(f"\n--- WhatsApp message preview ---\n{msg}\n--------------------------------")
    print("Sending to WhatsApp...")

    ok = send(msg)
    if ok:
        print("SUCCESS — check your WhatsApp!")
    else:
        print("FAILED — check bot.log for Twilio errors.")
    break
else:
    print("No AI articles found in last 24h.")
