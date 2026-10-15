"""Poll an IMAP mailbox and forward each new email to WhatsApp recipients."""
from __future__ import annotations

import argparse
import imaplib
import json
import logging
import re
import time
from pathlib import Path

from .config import Config
from .parser import format_message, parse_email
from .senders import Sender, build_sender

log = logging.getLogger("email_to_whatsapp")
SEND_ATTEMPTS = 3


class State:
    """Remembers the last processed UID so restarts don't resend or skip mail."""

    def __init__(self, path: Path):
        self.path = path
        data = json.loads(path.read_text()) if path.is_file() else {}
        self.uidvalidity: int | None = data.get("uidvalidity")
        self.last_uid: int | None = data.get("last_uid")

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"uidvalidity": self.uidvalidity, "last_uid": self.last_uid}))
        tmp.replace(self.path)


def _status_value(conn: imaplib.IMAP4_SSL, folder: str, item: str) -> int:
    typ, data = conn.status(folder, f"({item})")
    if typ != "OK":
        raise RuntimeError(f"STATUS {item} failed: {data}")
    match = re.search(rf"{item} (\d+)", data[0].decode())
    if not match:
        raise RuntimeError(f"Unexpected STATUS response: {data}")
    return int(match.group(1))


def deliver(sender: Sender, recipients: list[str], text: str) -> None:
    for to in recipients:
        for attempt in range(1, SEND_ATTEMPTS + 1):
            try:
                sender.send(to, text)
                log.info("Sent to %s", to)
                break
            except Exception as exc:  # noqa: BLE001 - log and retry any delivery error
                detail = getattr(getattr(exc, "response", None), "text", "") or ""
                log.warning("Send to %s failed (attempt %d/%d): %s %s", to, attempt, SEND_ATTEMPTS, exc, detail[:300])
                if attempt < SEND_ATTEMPTS:
                    time.sleep(2**attempt)
        else:
            log.error("Giving up on %s for this email", to)


def check_mailbox(cfg: Config, sender: Sender, state: State, process_existing: bool = False) -> None:
    conn = imaplib.IMAP4_SSL(cfg.imap_host, cfg.imap_port)
    try:
        conn.login(cfg.imap_user, cfg.imap_password)
        folder = f'"{cfg.imap_folder}"'
        uidvalidity = _status_value(conn, folder, "UIDVALIDITY")
        uidnext = _status_value(conn, folder, "UIDNEXT")

        if state.uidvalidity != uidvalidity or state.last_uid is None:
            # First run (or mailbox was rebuilt): start from now instead of
            # blasting the whole inbox to WhatsApp.
            state.uidvalidity = uidvalidity
            state.last_uid = 0 if process_existing else uidnext - 1
            state.save()
            log.info("Initialized state at UID %s", state.last_uid)

        conn.select(folder, readonly=True)
        typ, data = conn.uid("search", None, f"UID {state.last_uid + 1}:*")
        if typ != "OK":
            raise RuntimeError(f"SEARCH failed: {data}")
        # "N:*" always matches the highest UID even if it's <= N, so filter.
        uids = sorted(int(u) for u in data[0].split() if int(u) > state.last_uid)

        for uid in uids:
            typ, msg_data = conn.uid("fetch", str(uid), "(BODY.PEEK[])")
            raw = next((part[1] for part in msg_data if isinstance(part, tuple)), None)
            if typ != "OK" or raw is None:
                log.warning("Could not fetch UID %s, skipping", uid)
            else:
                email = parse_email(raw)
                if cfg.sender_filter and not any(f in email.sender_address for f in cfg.sender_filter):
                    log.info("UID %s from %s ignored by SENDER_FILTER", uid, email.sender_address)
                else:
                    log.info("Forwarding UID %s: %s", uid, email.subject)
                    deliver(sender, cfg.recipients, format_message(email, cfg.max_chars))
            state.last_uid = uid
            state.save()
    finally:
        try:
            conn.logout()
        except Exception:  # noqa: BLE001
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="check the mailbox once and exit")
    parser.add_argument("--process-existing", action="store_true",
                        help="on first run, forward emails already in the folder (default: only new ones)")
    parser.add_argument("--test", metavar="TEXT", help="send TEXT to all recipients and exit")
    parser.add_argument("--env-file", default=".env")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = Config.from_env(args.env_file)
    sender = build_sender(cfg.provider, cfg.provider_settings)

    if args.test:
        deliver(sender, cfg.recipients, args.test)
        return

    state = State(cfg.state_file)
    log.info("Watching %s/%s via %s -> %s", cfg.imap_user, cfg.imap_folder, cfg.provider, ", ".join(cfg.recipients))
    while True:
        try:
            check_mailbox(cfg, sender, state, args.process_existing)
        except Exception:  # noqa: BLE001 - keep the service alive across transient failures
            log.exception("Mailbox check failed; retrying in %ss", cfg.poll_seconds)
        if args.once:
            break
        time.sleep(cfg.poll_seconds)


if __name__ == "__main__":
    main()
