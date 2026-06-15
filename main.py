import time
import logging

from config import POLL_INTERVAL_MINUTES
from news_fetcher import fetch_all
from summarizer import quick_filter, summarize
from whatsapp_sender import send, format_message
from tracker import ArticleTracker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

SEND_DELAY_SECONDS = 3


def run_poll(tracker: ArticleTracker) -> int:
    articles = fetch_all()
    log.info(f"Fetched {len(articles)} total articles from all sources.")

    new = [a for a in articles if a.get("url") and not tracker.is_seen(a["url"])]
    log.info(f"New (unseen) articles: {len(new)}")

    sent_count = 0
    for article in new:
        url = article["url"]
        tracker.mark(url)  # mark before processing so a crash won't re-send

        if not quick_filter(article):
            log.info(f"  [SKIP keyword] {article['title'][:70]}")
            continue

        log.info(f"  [PROCESS] {article['title'][:70]}")
        result = summarize(article)
        if result is None:
            log.info(f"    → Groq filtered out (not AI-relevant)")
            continue

        log.info(f"    → type={result['type']}  summary={result['summary'][:60]}...")
        message = format_message(article, result["summary"], result["type"])
        if send(message):
            log.info(f"    → WhatsApp sent OK")
            sent_count += 1
            time.sleep(SEND_DELAY_SECONDS)
        else:
            log.warning(f"    → WhatsApp send FAILED")

    tracker.save()
    return sent_count


def initial_index(tracker: ArticleTracker):
    """Seed the tracker with existing articles so we don't send old news on startup."""
    log.info("First run: seeding tracker with existing articles (nothing will be sent)...")
    articles = fetch_all(lookback_minutes=60 * 24)
    urls = [a["url"] for a in articles if a.get("url")]
    tracker.mark_all(urls)
    tracker.save()
    log.info(f"Seeded {len(urls)} URLs. Now watching for NEW articles only.")


def main():
    log.info(f"AI News Alert Bot starting — poll every {POLL_INTERVAL_MINUTES} min")

    tracker = ArticleTracker().load()

    if not tracker._seen:
        initial_index(tracker)

    while True:
        log.info("─" * 50)
        log.info("Polling sources...")
        try:
            count = run_poll(tracker)
            if count:
                log.info(f"✓ Sent {count} message(s) to WhatsApp.")
            else:
                log.info("No new articles this cycle — sleeping.")
        except Exception as e:
            log.error(f"Unhandled error: {e}", exc_info=True)

        log.info(f"Next poll in {POLL_INTERVAL_MINUTES} minutes.")
        time.sleep(POLL_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
