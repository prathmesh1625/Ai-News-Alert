"""Verifies KEEP/SKIP on representative examples — no WhatsApp sends."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from summarizer import summarize

samples = [
    # Should KEEP — tools / updates / useful news
    {"title": "OpenAI launches new Agent Builder for creating custom AI assistants",
     "summary": "OpenAI released Agent Builder, a no-code tool that lets anyone build and deploy custom AI agents that can browse the web and use tools."},
    {"title": "Anthropic releases Claude with 2x faster responses and computer use",
     "summary": "The new Claude model can now control a computer, click buttons and fill forms, and responds twice as fast as before."},
    {"title": "Google's NotebookLM adds video overviews and mobile app",
     "summary": "NotebookLM now generates video summaries from your documents and launches a dedicated iOS and Android app."},
    # Should SKIP — noise
    {"title": "AI startup raises $200M in Series C funding round",
     "summary": "The company plans to use the funds to expand its sales team."},
    {"title": "Why AI might change everything in the next decade",
     "summary": "An opinion piece speculating about the long-term future of artificial intelligence."},
]

for s in samples:
    r = summarize(s)
    tag = f"KEEP/{r['type']}" if r else "SKIP"
    print(f"[{tag:11}] {s['title'][:65]}")
    if r:
        print(f"              → {r['summary'][:110]}")
