"""
Render free-tier entrypoint.

Render's free plan only offers a *web service* (background workers/cron are
paid), and it spins down after 15 min with no inbound traffic. So we:
  • bind to $PORT and answer health checks (keeps Render happy),
  • run the existing poll loop (main.main) in a background daemon thread,
  • expose POST /whatsapp so you can text the bot and query saved tools.

Keep it awake with a free external pinger (e.g. UptimeRobot) hitting the URL
every ~5 min — otherwise the service sleeps and the loop stops.
"""

import os
import threading
import logging
from urllib.parse import parse_qs
from xml.sax.saxutils import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from main import main as run_loop
import commands
from config import TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_TO

log = logging.getLogger("web")

# Set to "0" to bypass Twilio signature validation (debugging only).
_VALIDATE = os.getenv("TWILIO_VALIDATE", "1") != "0"


def _twiml(message: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{escape(message)}</Message></Response>"
    ).encode("utf-8")


def _signature_ok(handler, url: str, params: dict) -> bool:
    if not _VALIDATE:
        return True
    if not TWILIO_AUTH_TOKEN:
        log.warning("No TWILIO_AUTH_TOKEN — cannot validate webhook signature.")
        return False
    try:
        from twilio.request_validator import RequestValidator
        signature = handler.headers.get("X-Twilio-Signature", "")
        return RequestValidator(TWILIO_AUTH_TOKEN).validate(url, params, signature)
    except Exception as e:
        log.warning(f"Signature validation error: {e}")
        return False


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"AI News Alert is running.\n")

    def do_HEAD(self):
        # Uptime pingers (e.g. UptimeRobot) probe with HEAD by default; without
        # this the base handler returns 501 and the monitor reports "down".
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()

    def do_POST(self):
        if self.path.rstrip("/") != "/whatsapp":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        params = {k: v[0] for k, v in parse_qs(raw).items()}

        # Reconstruct the public URL Twilio signed (behind Render's TLS proxy).
        proto = self.headers.get("X-Forwarded-Proto", "https")
        host = self.headers.get("Host", "")
        url = f"{proto}://{host}{self.path}"

        if not _signature_ok(self, url, params):
            log.warning("Rejected webhook: bad/missing Twilio signature.")
            self.send_response(403)
            self.end_headers()
            return

        # Only answer the owner's number; ignore anyone else who finds the URL.
        sender = params.get("From", "")
        if TWILIO_WHATSAPP_TO and sender != TWILIO_WHATSAPP_TO:
            log.warning(f"Ignoring message from non-owner: {sender}")
            self._reply("")  # empty TwiML = no message sent
            return

        body = params.get("Body", "")
        log.info(f"Incoming WhatsApp: {body!r}")
        try:
            reply = commands.handle(body)
        except Exception as e:
            log.error(f"Command handling error: {e}", exc_info=True)
            reply = "Sorry — something went wrong handling that. Try 'help'."
        self._reply(reply)

    def _reply(self, message: str):
        payload = _twiml(message)
        self.send_response(200)
        self.send_header("Content-Type", "application/xml")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        # Silence per-request access logs (the keep-alive pinger is noisy).
        pass


def main():
    # Start polling in the background so the web server can answer health checks.
    threading.Thread(target=run_loop, daemon=True).start()

    port = int(os.getenv("PORT", "10000"))
    log.info(f"Health server listening on :{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
