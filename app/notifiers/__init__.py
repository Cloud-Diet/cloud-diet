"""Notification delivery facade."""

from __future__ import annotations

import logging
import sys

from app.config import Settings
from app.notifiers.discord_notifier import send_discord_message
from app.notifiers.slack_notifier import send_slack_message

logger = logging.getLogger(__name__)


def send_message(message: str, settings: Settings) -> None:
    """Send a message to the configured notification channel."""

    notifier = settings.notification.notifier
    if notifier == "discord":
        send_discord_message(message, settings)
        return
    if notifier == "slack":
        send_slack_message(message, settings)
        return
    if notifier == "console":
        _print_console(message)
        return
    if notifier == "none":
        logger.info("Notifier disabled; message was not sent")
        return

    raise ValueError("NOTIFIER must be one of: discord, slack, console, none")


def _print_console(message: str) -> None:
    """Print Korean messages safely even on non-UTF-8 Windows consoles."""

    try:
        print(message)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((message + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
