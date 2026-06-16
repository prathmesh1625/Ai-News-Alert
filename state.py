"""
Tiny persisted state for Twilio budget control.

Lives in bot_state.json (persisted via the storage backend alongside
seen_articles.json) so limits survive across runs/restarts. Two jobs:
  • cap total WhatsApp messages per UTC day  -> protect the Twilio free tier
  • space out evergreen fallbacks            -> avoid spammy quiet-period sends
"""

import logging
from datetime import datetime, timezone

import storage
from config import MAX_SENDS_PER_DAY, FALLBACK_GAP_HOURS

log = logging.getLogger(__name__)

STATE_FILE = "bot_state.json"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class SendBudget:
    """Tracks how many messages went out today and when the last fallback was."""

    def __init__(self):
        self.day = _today()
        self.sent_today = 0
        self.last_fallback_iso: str | None = None

    def load(self) -> "SendBudget":
        data = storage.read_json(STATE_FILE, None)
        if data:
            self.last_fallback_iso = data.get("last_fallback_iso")
            # Reset the daily counter when the UTC day rolls over.
            if data.get("day") == self.day:
                self.sent_today = int(data.get("sent_today", 0))
        return self

    def save(self):
        storage.write_json(
            STATE_FILE,
            {
                "day": self.day,
                "sent_today": self.sent_today,
                "last_fallback_iso": self.last_fallback_iso,
            },
        )

    # ── budget checks ──────────────────────────────────────────────────────
    def can_send(self) -> bool:
        """True while we're under the daily message cap."""
        return self.sent_today < MAX_SENDS_PER_DAY

    def remaining(self) -> int:
        return max(0, MAX_SENDS_PER_DAY - self.sent_today)

    def record_send(self):
        self.sent_today += 1

    def fallback_due(self) -> bool:
        """True if enough hours have passed since the last evergreen send."""
        if not self.last_fallback_iso:
            return True
        try:
            last = datetime.fromisoformat(self.last_fallback_iso)
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
        except Exception:
            return True
        hours = (datetime.now(timezone.utc) - last).total_seconds() / 3600
        return hours >= FALLBACK_GAP_HOURS

    def record_fallback(self):
        self.last_fallback_iso = datetime.now(timezone.utc).isoformat()
