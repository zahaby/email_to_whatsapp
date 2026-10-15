"""WhatsApp delivery backends."""
from __future__ import annotations

import logging
from typing import Protocol
from urllib.parse import quote

import requests

log = logging.getLogger(__name__)
TIMEOUT = 20


class Sender(Protocol):
    def send(self, to: str, text: str) -> None: ...


def _normalize(number: str) -> str:
    """'+20 100-123 4567' -> '+201001234567'."""
    digits = "".join(ch for ch in number if ch.isdigit())
    return "+" + digits


class TwilioSender:
    """Twilio WhatsApp API (works with the free Twilio sandbox for testing)."""

    def __init__(self, settings: dict[str, str]):
        self.sid = settings["TWILIO_ACCOUNT_SID"]
        self.token = settings["TWILIO_AUTH_TOKEN"]
        sender = settings["TWILIO_WHATSAPP_FROM"]
        self.from_ = sender if sender.startswith("whatsapp:") else f"whatsapp:{_normalize(sender)}"

    def send(self, to: str, text: str) -> None:
        resp = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{self.sid}/Messages.json",
            auth=(self.sid, self.token),
            data={"From": self.from_, "To": f"whatsapp:{_normalize(to)}", "Body": text},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()


class MetaCloudSender:
    """Meta WhatsApp Cloud API.

    Free-form text only reaches a recipient who messaged your business number in
    the last 24h. Set META_TEMPLATE_NAME to send via an approved template whose
    body has a single {{1}} parameter instead (works any time).
    """

    def __init__(self, settings: dict[str, str]):
        self.token = settings["META_ACCESS_TOKEN"]
        version = settings.get("META_API_VERSION", "v21.0")
        self.url = f"https://graph.facebook.com/{version}/{settings['META_PHONE_NUMBER_ID']}/messages"
        self.template = settings.get("META_TEMPLATE_NAME")
        self.lang = settings.get("META_TEMPLATE_LANG", "en_US")

    def send(self, to: str, text: str) -> None:
        payload: dict = {"messaging_product": "whatsapp", "to": _normalize(to).lstrip("+")}
        if self.template:
            # Template parameters cannot contain newlines/tabs or 4+ consecutive spaces.
            flat = " | ".join(line for line in text.splitlines() if line.strip())
            payload.update(
                type="template",
                template={
                    "name": self.template,
                    "language": {"code": self.lang},
                    "components": [
                        {"type": "body", "parameters": [{"type": "text", "text": flat[:1000]}]}
                    ],
                },
            )
        else:
            payload.update(type="text", text={"body": text, "preview_url": False})
        resp = requests.post(
            self.url,
            headers={"Authorization": f"Bearer {self.token}"},
            json=payload,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()


class CallMeBotSender:
    """CallMeBot free personal API. Each recipient registers once and gets an API key.

    CALLMEBOT_API_KEYS maps numbers to keys: "+201001234567:123456,+201112345678:654321".
    """

    def __init__(self, settings: dict[str, str]):
        self.keys: dict[str, str] = {}
        for pair in settings["CALLMEBOT_API_KEYS"].split(","):
            number, _, key = pair.strip().rpartition(":")
            if number and key:
                self.keys[_normalize(number)] = key

    def send(self, to: str, text: str) -> None:
        number = _normalize(to)
        key = self.keys.get(number)
        if not key:
            raise ValueError(f"No CallMeBot API key configured for {number}")
        resp = requests.get(
            "https://api.callmebot.com/whatsapp.php"
            f"?phone={quote(number)}&text={quote(text)}&apikey={quote(key)}",
            timeout=TIMEOUT,
        )
        resp.raise_for_status()


def build_sender(provider: str, settings: dict[str, str]) -> Sender:
    return {"twilio": TwilioSender, "meta": MetaCloudSender, "callmebot": CallMeBotSender}[provider](settings)
