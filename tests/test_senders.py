from email_to_whatsapp import senders


class _Resp:
    def raise_for_status(self):
        pass


def test_waha_payload(monkeypatch):
    calls = []
    monkeypatch.setattr(senders.requests, "post", lambda url, **kw: calls.append((url, kw)) or _Resp())
    s = senders.build_sender("waha", {"WAHA_URL": "http://waha:3000/", "WAHA_API_KEY": "k"})
    s.send("+20 100 123 4567", "hi")
    url, kw = calls[0]
    assert url == "http://waha:3000/api/sendText"
    assert kw["headers"] == {"X-Api-Key": "k"}
    assert kw["json"] == {"session": "default", "chatId": "201001234567@c.us", "text": "hi", "linkPreview": False}
