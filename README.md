# email_to_whatsapp

Watches an email inbox (IMAP) and forwards every new email (sender, subject, body and attachment names) as a WhatsApp message to one or more numbers.

```
New mail in INBOX ──► email_to_whatsapp ──► WhatsApp ──► +20100… (you)
                                                     └──► +20111… (Riham)
```

## Quick start (Docker)

```bash
cp .env.example .env          # fill in mailbox, both numbers, WAHA passwords
docker compose up -d          # starts WAHA + the forwarder
```

Then link WhatsApp once (see below) and send a test:

```bash
docker compose run --rm forwarder python -m email_to_whatsapp --test "hello"
docker compose logs -f forwarder
```

Without Docker for the forwarder: `pip install -r requirements.txt`, set `WAHA_URL=http://localhost:3000` in `.env`, and run `python -m email_to_whatsapp`.

## Mailbox setup

| Provider | `IMAP_HOST` | Password |
|---|---|---|
| Gmail | `imap.gmail.com` | Turn on 2-Step Verification, then create an **App Password** |
| Outlook / Office 365 | `outlook.office365.com` | Account password or app password |
| Yahoo | `imap.mail.yahoo.com` | App password |

The mailbox is opened **read-only** and messages are fetched with `BODY.PEEK`, so nothing is marked as read, moved or deleted. On the first run, emails already in the folder are skipped (use `--process-existing` to forward them too). The last-forwarded UID is kept in `state.json`, so restarts don't resend or miss mail.

Set `SENDER_FILTER` to forward only mail from specific senders or domains.

## WhatsApp setup (WAHA, default)

[WAHA](https://github.com/devlikeapro/waha) runs WhatsApp Web in a container and exposes an HTTP API. Emails are sent **from the WhatsApp account you link** to the numbers in `WHATSAPP_RECIPIENTS`.

1. **Use a spare number if you can** (a cheap second SIM with WhatsApp installed). Messages you send to yourself land silently in "Message yourself" with no notification, and WAHA is unofficial, so WhatsApp could ban a number it sees as automated. A spare number keeps your main account safe and makes alerts notify both you and Riham.
2. Open <http://localhost:3000/dashboard> on the machine running Docker and log in with `WAHA_DASHBOARD_USERNAME` / `WAHA_DASHBOARD_PASSWORD`. When it asks for the API key, use `WAHA_API_KEY`.
3. The `default` session shows a QR code. On the phone: WhatsApp → Settings → Linked devices → Link a device → scan it. The status changes to **WORKING**.
4. Have you and Riham save the spare number as a contact (helps avoid spam filtering) and send it one message, such as "hi".

The login is saved in `./waha-sessions`, so restarts don't need a new scan. If the phone is offline for about 14 days or the device is unlinked, scan again. While WhatsApp is unreachable, emails are held and retried on every poll, so nothing is lost.

### Other providers

Set `WHATSAPP_PROVIDER` to `twilio`, `meta` or `callmebot` and fill in the matching block in `.env.example`. Meta's WhatsApp Cloud API is the official, ban-free route but needs a business account and an approved template.

## Options

| Variable | Default | Meaning |
|---|---|---|
| `IMAP_FOLDER` | `INBOX` | Folder/label to watch |
| `POLL_SECONDS` | `30` | How often to check for new mail |
| `MAX_CHARS` | `1500` | Long bodies are truncated (Twilio's limit is 1600) |
| `STATE_FILE` | `state.json` | Where the last processed UID is saved |

CLI flags: `--once` (check once and exit, useful from cron), `--process-existing`, `--test TEXT`, `--env-file PATH`.

## Development

```bash
pip install pytest -r requirements.txt
python -m pytest
```
