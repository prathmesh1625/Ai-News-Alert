from news_fetcher import fetch_all

articles = fetch_all(lookback_minutes=240)  # last 4 hours
print(f"Fetched {len(articles)} articles\n")
for a in articles[:8]:
    print(f"  [{a['source']}] {a['title'][:75]}")
