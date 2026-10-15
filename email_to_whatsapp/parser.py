"""Turn a raw RFC 822 email into a short WhatsApp-friendly text message."""
from __future__ import annotations

import html
import re
from dataclasses import dataclass
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parseaddr


@dataclass
class ParsedEmail:
    sender: str
    sender_address: str
    subject: str
    body: str
    attachments: list[str]


def _html_to_text(markup: str) -> str:
    markup = re.sub(r"(?is)<(script|style).*?</\1>", "", markup)
    markup = re.sub(r"(?i)<br\s*/?>", "\n", markup)
    markup = re.sub(r"(?i)</(p|div|tr|li|h[1-6])>", "\n", markup)
    text = re.sub(r"<[^>]+>", "", markup)
    return html.unescape(text)


def _clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\xa0", " ")
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def parse_email(raw: bytes) -> ParsedEmail:
    msg: EmailMessage = BytesParser(policy=policy.default).parsebytes(raw)  # type: ignore[assignment]

    sender = str(msg.get("From", ""))
    _, address = parseaddr(sender)
    subject = str(msg.get("Subject", "")).strip() or "(no subject)"

    body = ""
    part = msg.get_body(preferencelist=("plain",))
    if part is not None:
        body = part.get_content()
    else:
        part = msg.get_body(preferencelist=("html",))
        if part is not None:
            body = _html_to_text(part.get_content())

    attachments = [a.get_filename() or "unnamed" for a in msg.iter_attachments()]

    return ParsedEmail(
        sender=sender,
        sender_address=address.lower(),
        subject=subject,
        body=_clean(body),
        attachments=attachments,
    )


def format_message(email: ParsedEmail, max_chars: int = 1500) -> str:
    header = f"📧 *New email*\n*From:* {email.sender}\n*Subject:* {email.subject}"
    footer = ""
    if email.attachments:
        footer = "\n\n📎 Attachments: " + ", ".join(email.attachments)

    budget = max_chars - len(header) - len(footer) - 2
    body = email.body or "(empty body)"
    if budget <= 0:
        body = ""
    elif len(body) > budget:
        marker = "\n…[truncated]"
        body = body[: max(budget - len(marker), 0)].rstrip() + marker

    message = header + ("\n\n" + body if body else "") + footer
    return message[:max_chars]
