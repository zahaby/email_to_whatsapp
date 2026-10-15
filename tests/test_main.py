from email.message import EmailMessage

from email_to_whatsapp import main as m
from email_to_whatsapp.config import Config


def _email(i, sender="a@x.com"):
    msg = EmailMessage()
    msg["From"] = sender
    msg["Subject"] = f"msg {i}"
    msg.set_content(f"body {i}")
    return bytes(msg)


class FakeIMAP:
    mailbox: dict[int, bytes] = {}
    uidvalidity = 7

    def __init__(self, host, port):
        pass

    def login(self, u, p):
        return "OK", [b""]

    def status(self, folder, items):
        nxt = max(self.mailbox, default=0) + 1
        key = items.strip("()")
        val = self.uidvalidity if key == "UIDVALIDITY" else nxt
        return "OK", [f'"INBOX" ({key} {val})'.encode()]

    def select(self, folder, readonly=False):
        assert readonly
        return "OK", [b""]

    def uid(self, cmd, *args):
        if cmd == "search":
            start = int(args[1].split()[1].split(":")[0])
            hits = [u for u in self.mailbox if u >= start] or [max(self.mailbox, default=0)]
            return "OK", [" ".join(str(u) for u in hits if u).encode()]
        uid = int(args[0])
        return "OK", [(b"1 (BODY[] {n}", self.mailbox[uid]), b")"]

    def logout(self):
        pass


class RecordingSender:
    def __init__(self):
        self.sent = []

    def send(self, to, text):
        self.sent.append((to, text))


def _cfg(tmp_path, **kw):
    base = dict(
        imap_host="h", imap_port=993, imap_user="u", imap_password="p", imap_folder="INBOX",
        poll_seconds=1, state_file=tmp_path / "state.json", sender_filter=[], max_chars=1500,
        provider="twilio", recipients=["+201", "+202"],
    )
    base.update(kw)
    return Config(**base)


def test_only_new_mail_is_forwarded_to_all_recipients(tmp_path, monkeypatch):
    FakeIMAP.mailbox = {1: _email(1), 2: _email(2)}
    monkeypatch.setattr(m.imaplib, "IMAP4_SSL", FakeIMAP)
    cfg, sender = _cfg(tmp_path), RecordingSender()

    m.check_mailbox(cfg, sender, m.State(cfg.state_file))
    assert sender.sent == []  # existing mail is skipped on first run

    FakeIMAP.mailbox[3] = _email(3)
    m.check_mailbox(cfg, sender, m.State(cfg.state_file))  # fresh State => reads from disk
    assert [to for to, _ in sender.sent] == ["+201", "+202"]
    assert "msg 3" in sender.sent[0][1]

    m.check_mailbox(cfg, sender, m.State(cfg.state_file))
    assert len(sender.sent) == 2  # no duplicates


def test_sender_filter(tmp_path, monkeypatch):
    FakeIMAP.mailbox = {1: _email(1, "spam@x.com"), 2: _email(2, "Boss <boss@corp.com>")}
    monkeypatch.setattr(m.imaplib, "IMAP4_SSL", FakeIMAP)
    cfg, sender = _cfg(tmp_path, sender_filter=["@corp.com"]), RecordingSender()

    m.check_mailbox(cfg, sender, m.State(cfg.state_file), process_existing=True)
    assert len(sender.sent) == 2 and all("msg 2" in t for _, t in sender.sent)


def test_failed_recipient_does_not_block_others(monkeypatch):
    monkeypatch.setattr(m.time, "sleep", lambda s: None)

    class Flaky(RecordingSender):
        def send(self, to, text):
            if to == "+201":
                raise RuntimeError("boom")
            super().send(to, text)

    s = Flaky()
    m.deliver(s, ["+201", "+202"], "hi")
    assert s.sent == [("+202", "hi")]
