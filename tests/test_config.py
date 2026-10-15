import pytest

from email_to_whatsapp.config import Config

BASE = {"IMAP_HOST": "h", "IMAP_USER": "u", "IMAP_PASSWORD": "p",
        "WHATSAPP_RECIPIENTS": "+20 100 000 0001,+201000000002"}


def test_callmebot_is_default(monkeypatch):
    for k, v in {**BASE, "CALLMEBOT_API_KEYS": "+201000000001:1,+201000000002:2"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("WHATSAPP_PROVIDER", raising=False)
    assert Config.from_env(dotenv=None).provider == "callmebot"


def test_callmebot_missing_key_fails_fast(monkeypatch):
    for k, v in {**BASE, "CALLMEBOT_API_KEYS": "+201000000001:1"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("WHATSAPP_PROVIDER", raising=False)
    with pytest.raises(SystemExit, match="201000000002"):
        Config.from_env(dotenv=None)
