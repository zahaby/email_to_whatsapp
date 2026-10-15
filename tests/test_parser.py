from email.message import EmailMessage

from email_to_whatsapp.parser import format_message, parse_email


def _raw(plain=None, html=None, attach=False):
    msg = EmailMessage()
    msg["From"] = "Alice <Alice@Example.com>"
    msg["Subject"] = "Hello there"
    if plain is not None:
        msg.set_content(plain)
    if html is not None:
        if plain is None:
            msg.set_content(html, subtype="html")
        else:
            msg.add_alternative(html, subtype="html")
    if attach:
        msg.add_attachment(b"data", maintype="application", subtype="pdf", filename="invoice.pdf")
    return bytes(msg)


def test_plain_body():
    e = parse_email(_raw(plain="Line 1\n\n\n\nLine 2"))
    assert e.sender_address == "alice@example.com"
    assert e.subject == "Hello there"
    assert e.body == "Line 1\n\nLine 2"


def test_prefers_plain_over_html():
    e = parse_email(_raw(plain="plain text", html="<p>html</p>"))
    assert e.body == "plain text"


def test_html_only_is_converted():
    e = parse_email(_raw(html="<style>x{}</style><p>Hi&nbsp;<b>Bob</b></p><br>Bye"))
    assert e.body == "Hi Bob\n\nBye"


def test_attachments_listed():
    e = parse_email(_raw(plain="see attached", attach=True))
    assert e.attachments == ["invoice.pdf"]
    assert "invoice.pdf" in format_message(e)


def test_truncation_respects_limit():
    e = parse_email(_raw(plain="x" * 5000))
    text = format_message(e, max_chars=300)
    assert len(text) <= 300
    assert text.endswith("[truncated]")
    assert "*Subject:* Hello there" in text
