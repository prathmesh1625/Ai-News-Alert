import logging
from twilio.rest import Client
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, TWILIO_WHATSAPP_TO

log = logging.getLogger(__name__)
_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send(message: str) -> bool:
    try:
        msg = _client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=TWILIO_WHATSAPP_TO,
            body=message,
        )
        log.info(f"WhatsApp sent — SID: {msg.sid}")
        return True
    except Exception as e:
        log.error(f"Twilio send error: {e}")
        return False


def format_message(article: dict, summary: str, article_type: str = "news") -> str:
    title = article.get("title", "No title")
    url = article.get("url", "")
    source = article.get("source", "Unknown")

    if article_type == "tool":
        header = "🛠️ *New AI Tool / Launch*"
        icon = "🚀"
    else:
        header = "🤖 *AI News Alert*"
        icon = "📝"

    msg = (
        f"{header}\n\n"
        f"📰 *{title}*\n\n"
        f"{icon} {summary}\n\n"
        f"🔗 {url}\n"
        f"📌 {source}"
    )
    return msg[:1580]
