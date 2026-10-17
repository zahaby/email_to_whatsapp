import pytest

from email_to_whatsapp.config import Config

BASE = {"IMAP_HOST": "h", "IMAP_USER": "u", "IMAP_PASSWORD": "p",
        "WHATSAPP_RECIPIENTS": "+20 100 000 0001,+201000000002"}


def test_waha_is_default(monkeypatch):
    for k, v in {**BASE, "WAHA_API_KEY": "k"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("WHATSAPP_PROVIDER", raising=False)
    cfg = Config.from_env(dotenv=None)
    assert cfg.provider == "waha" and cfg.provider_settings["WAHA_API_KEY"] == "k"


def test_callmebot_missing_key_fails_fast(monkeypatch):
    for k, v in {**BASE, "CALLMEBOT_API_KEYS": "+201000000001:1"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("WHATSAPP_PROVIDER", "callmebot")
    with pytest.raises(SystemExit, match="201000000002"):
        Config.from_env(dotenv=None)
