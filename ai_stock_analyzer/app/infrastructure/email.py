"""SMTP transport; credentials and reset URLs are never logged."""

import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


async def send_password_reset(recipient, token):
    url = settings.APP_PUBLIC_URL.rstrip("/") + "/reset-password#token=" + token
    message = EmailMessage()
    message["From"], message["To"] = settings.SMTP_FROM, recipient
    message["Subject"] = "Reset password AI Stock Analyzer"
    message.set_content(
        "Buka tautan berikut untuk mengganti password. Berlaku 30 menit dan hanya sekali pakai.\n"
        + url
        + "\nJika Anda tidak meminta reset, abaikan email ini."
    )

    def deliver():
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if settings.SMTP_USERNAME:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)

    await asyncio.to_thread(deliver)
