import os
import sys
import time
import logging

from config import POLL_INTERVAL_MINUTES, LOOKBACK_MINUTES, MAX_NEWS_PER_RUN
from news_fetcher import fetch_all
from summarizer import quick_filter, summarize
from whatsapp_sender import send, format_message
from tracker import ArticleTracker
from state import SendBudget
import evergreen

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


def _send_news(tracker: ArticleTracker, budget: SendBudget) -> int:
    """Priority 1: fresh AI news / tools. Returns how many were sent."""
    articles = fetch_all()
    log.info(f"Fetched {len(articles)} total articles from all sources.")

    new = [a for a in articles if a.get("url") and not tracker.is_seen(a["url"])]
    log.info(f"New (unseen) articles: {len(new)}")

    sent_count = 0
    for article in new:
        if sent_count >= MAX_NEWS_PER_RUN:
            log.info(f"  Hit MAX_NEWS_PER_RUN ({MAX_NEWS_PER_RUN}) — leaving the rest for next run.")
            break
        if not budget.can_send():
            log.info("  Daily Twilio budget reached — stopping news sends.")
            break

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
            budget.record_send()
            time.sleep(SEND_DELAY_SECONDS)
        else:
            log.warning(f"    → WhatsApp send FAILED")

    return sent_count


def _send_fallback(tracker: ArticleTracker, budget: SendBudget) -> int:
    """
    Priority 2 (existing tools) then 3 (tips). Only fires when there was no
    fresh news, the daily budget allows it, and enough time has passed since
    the last fallback. Sends at most one item per run.
    """
    if not budget.can_send():
        log.info("Fallback skipped — daily Twilio budget reached.")
        return 0
    if not budget.fallback_due():
        log.info("Fallback skipped — too soon since the last one (FALLBACK_GAP_HOURS).")
        return 0

    item = evergreen.pick_unseen(tracker)
    if item is None:
        log.info("Fallback skipped — every evergreen item already sent this week.")
        return 0

    tracker.mark(item["url"])
    message = format_message(item, item["summary"], item["type"])
    if send(message):
        log.info(f"  [FALLBACK {item['type']}] sent: {item['title'][:60]}")
        budget.record_send()
        budget.record_fallback()
        return 1

    log.warning(f"  [FALLBACK] send FAILED: {item['title'][:60]}")
    return 0


def run_poll(tracker: ArticleTracker, budget: SendBudget) -> int:
    news_sent = _send_news(tracker, budget)

    fallback_sent = 0
    if news_sent == 0:
        log.info("No fresh news this run — trying evergreen fallback.")
        fallback_sent = _send_fallback(tracker, budget)

    tracker.save()
    budget.save()
    return news_sent + fallback_sent


def initial_index(tracker: ArticleTracker):
    """Seed the tracker with existing articles so we don't send old news on startup."""
    log.info("First run: seeding tracker with existing articles (nothing will be sent)...")
    articles = fetch_all(lookback_minutes=60 * 24)
    urls = [a["url"] for a in articles if a.get("url")]
    tracker.mark_all(urls)
    tracker.save()
    log.info(f"Seeded {len(urls)} URLs. Now watching for NEW articles only.")


def run_once():
    """Single poll cycle — used by GitHub Actions / cron."""
    log.info("AI News Alert Bot — single run (cron mode)")
    tracker = ArticleTracker().load()

    if not tracker._seen:
        # No prior state (first ever run): seed only, send nothing.
        initial_index(tracker)
        return

    budget = SendBudget().load()
    log.info(f"Twilio budget: {budget.remaining()} of {budget.sent_today + budget.remaining()} sends left today.")

    try:
        count = run_poll(tracker, budget)
        log.info(f"✓ Sent {count} message(s)." if count else "Nothing sent this run.")
    except Exception as e:
        log.error(f"Unhandled error: {e}", exc_info=True)


def main():
    """Continuous loop — used when running locally / on an always-on host."""
    log.info(f"AI News Alert Bot starting — poll every {POLL_INTERVAL_MINUTES} min")

    tracker = ArticleTracker().load()

    if not tracker._seen:
        initial_index(tracker)

    while True:
        log.info("─" * 50)
        log.info("Polling sources...")
        budget = SendBudget().load()
        try:
            count = run_poll(tracker, budget)
            if count:
                log.info(f"✓ Sent {count} message(s) to WhatsApp.")
            else:
                log.info("Nothing sent this cycle — sleeping.")
        except Exception as e:
            log.error(f"Unhandled error: {e}", exc_info=True)

        log.info(f"Next poll in {POLL_INTERVAL_MINUTES} minutes.")
        time.sleep(POLL_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    if os.getenv("RUN_ONCE") == "1" or "--once" in sys.argv:
        run_once()
    else:
        main()
