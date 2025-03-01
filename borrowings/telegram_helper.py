import requests
from django.conf import settings


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": message,
    }
    response = requests.post(url, json=payload)
    return response.json()
