"""Discord webhook notifier."""

from __future__ import annotations

import requests

from app.config import Settings


def send_discord_message(message: str, settings: Settings) -> None:
    """Send a message to a Discord Incoming Webhook URL."""

    webhook_url = settings.notification.discord_webhook_url
    if not webhook_url:
        raise ValueError("DISCORD_WEBHOOK_URL is required when NOTIFIER=discord")

    for chunk in _chunk_message(message, limit=1900):
        response = requests.post(webhook_url, json={"content": chunk}, timeout=15)
        response.raise_for_status()


def _chunk_message(message: str, limit: int) -> list[str]:
    """Split long webhook messages into API-safe chunks."""

    if len(message) <= limit:
        return [message]

    chunks: list[str] = []
    current = ""
    for line in message.splitlines():
        if len(current) + len(line) + 1 > limit:
            chunks.append(current.strip())
            current = line
        else:
            current = f"{current}\n{line}" if current else line

    if current:
        chunks.append(current.strip())
    return chunks

