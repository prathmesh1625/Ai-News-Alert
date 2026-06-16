"""
Render free-tier entrypoint.

Render's free plan only offers a *web service* (background workers/cron are
paid), and it spins down after 15 min with no inbound traffic. So we:
  • bind to $PORT and answer health checks (keeps Render happy),
  • run the existing poll loop (main.main) in a background daemon thread.

Keep it awake with a free external pinger (e.g. UptimeRobot) hitting the URL
every ~5 min — otherwise the service sleeps and the loop stops.
"""

import os
import threading
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from main import main as run_loop

log = logging.getLogger("web")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"AI News Alert is running.\n")

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
