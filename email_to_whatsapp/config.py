"""Configuration loaded from environment variables (optionally via a .env file)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader: KEY=VALUE lines, existing env vars win."""
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def _list(name: str) -> list[str]:
    return [v.strip() for v in os.environ.get(name, "").split(",") if v.strip()]


@dataclass
class Config:
    imap_host: str
    imap_port: int
    imap_user: str
    imap_password: str
    imap_folder: str
    poll_seconds: int
    state_file: Path
    sender_filter: list[str]
    max_chars: int

    provider: str
    recipients: list[str]
    provider_settings: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls, dotenv: str | None = ".env") -> "Config":
        if dotenv:
            _load_dotenv(Path(dotenv))

        provider = os.environ.get("WHATSAPP_PROVIDER", "twilio").strip().lower()
        settings_keys = {
            "twilio": ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_WHATSAPP_FROM"],
            "meta": ["META_ACCESS_TOKEN", "META_PHONE_NUMBER_ID"],
            "callmebot": ["CALLMEBOT_API_KEYS"],
        }
        if provider not in settings_keys:
            raise SystemExit(
                f"Unknown WHATSAPP_PROVIDER '{provider}'. Use one of: {', '.join(settings_keys)}"
            )
        settings = {k: _require(k) for k in settings_keys[provider]}
        # Optional provider settings
        for k in ("META_TEMPLATE_NAME", "META_TEMPLATE_LANG", "META_API_VERSION"):
            if os.environ.get(k):
                settings[k] = os.environ[k].strip()

        recipients = _list("WHATSAPP_RECIPIENTS")
        if not recipients:
            raise SystemExit("WHATSAPP_RECIPIENTS must list at least one number, e.g. +201001234567,+201112345678")

        return cls(
            imap_host=_require("IMAP_HOST"),
            imap_port=int(os.environ.get("IMAP_PORT", "993")),
            imap_user=_require("IMAP_USER"),
            imap_password=_require("IMAP_PASSWORD"),
            imap_folder=os.environ.get("IMAP_FOLDER", "INBOX"),
            poll_seconds=int(os.environ.get("POLL_SECONDS", "30")),
            state_file=Path(os.environ.get("STATE_FILE", "state.json")),
            sender_filter=[s.lower() for s in _list("SENDER_FILTER")],
            max_chars=int(os.environ.get("MAX_CHARS", "1500")),
            provider=provider,
            recipients=recipients,
            provider_settings=settings,
        )
