# email_to_whatsapp

Watches an email inbox (IMAP) and forwards every new email (sender, subject, body and attachment names) as a WhatsApp message to one or more numbers.

```
New mail in INBOX ──► email_to_whatsapp ──► WhatsApp ──► +20100… (you)
                                                     └──► +20111… (Riham)
```

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env        # fill in mailbox, numbers, provider credentials
python -m email_to_whatsapp --test "Hello from email_to_whatsapp"   # check WhatsApp delivery
python -m email_to_whatsapp                                         # run forever
```

Or with Docker:

```bash
docker build -t email-to-whatsapp .
docker run -d --restart unless-stopped --env-file .env -v e2w-data:/data email-to-whatsapp
```

## Mailbox setup

| Provider | `IMAP_HOST` | Password |
|---|---|---|
| Gmail | `imap.gmail.com` | Turn on 2-Step Verification, then create an **App Password** |
| Outlook / Office 365 | `outlook.office365.com` | Account password or app password |
| Yahoo | `imap.mail.yahoo.com` | App password |

The mailbox is opened **read-only** and messages are fetched with `BODY.PEEK`, so nothing is marked as read, moved or deleted. On the first run, emails already in the folder are skipped (use `--process-existing` to forward them too). The last-forwarded UID is kept in `state.json`, so restarts don't resend or miss mail.

Set `SENDER_FILTER` to forward only mail from specific senders or domains.

## WhatsApp setup (CallMeBot, default)

CallMeBot is a free service for sending WhatsApp messages to your own phone. Each recipient (you and Riham) does this once:

1. Go to <https://www.callmebot.com/blog/free-api-whatsapp-messages/> and save the CallMeBot WhatsApp number shown there in your contacts.
2. Send it the WhatsApp message `I allow callmebot to send me messages`.
3. You'll get a reply with your personal **API key**.

Then put both numbers and keys in `.env`:

```
WHATSAPP_RECIPIENTS=+201000000001,+201000000002
CALLMEBOT_API_KEYS=+201000000001:123456,+201000000002:654321
```

and check it with `python -m email_to_whatsapp --test "hello"`.

CallMeBot is unofficial and meant for personal use: messages come from CallMeBot's number (not yours), it limits how often you can send, and there's no delivery guarantee. If you outgrow it, set `WHATSAPP_PROVIDER=twilio` or `meta` (see `.env.example`); Meta's WhatsApp Cloud API is the official route.

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
