"""
Quick end-to-end test: fetch one article, summarize it, send to WhatsApp.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from news_fetcher import fetch_all
from summarizer import quick_filter, summarize
from whatsapp_sender import send, format_message

articles = fetch_all(lookback_minutes=240)
print(f"Found {len(articles)} articles in last 4 hours\n")

sent = False
for article in articles:
    if not quick_filter(article):
        continue

    print(f"Testing with: {article['title'][:80]}")
    result = summarize(article)
    if result is None:
        print("  → Filtered out by GPT")
        continue

    print(f"  Type   : {result['type']}")
    print(f"  Summary: {result['summary'][:120]}")

    msg = format_message(article, result["summary"], result["type"])
    print(f"\nMessage preview:\n{msg}\n")

    ans = input("Send this to WhatsApp? [y/N]: ").strip().lower()
    if ans == "y":
        ok = send(msg)
        print("Sent!" if ok else "Failed to send.")
    sent = True
    break

if not sent:
    print("No articles passed filters in the last 4 hours. Try again later.")
