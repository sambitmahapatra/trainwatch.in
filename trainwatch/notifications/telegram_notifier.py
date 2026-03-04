"""Telegram bot notifier."""

from dataclasses import dataclass
from typing import Optional
import json
import urllib.request


@dataclass
class TelegramNotifier:
    bot_token: str
    chat_id: str
    api_base: str = "https://api.telegram.org"

    def send(self, message: str) -> None:
        if not message:
            raise ValueError("message must be a non-empty string")

        url = f"{self.api_base}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status >= 400:
                raise RuntimeError(f"Telegram API error: HTTP {resp.status}")
