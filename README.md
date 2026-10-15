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

## WhatsApp provider

WhatsApp has no free official API for personal accounts, so pick one of:

| `WHATSAPP_PROVIDER` | Best for | Notes |
|---|---|---|
| `twilio` | Fastest to get running | The free **sandbox** works right away: each recipient sends `join <code>` to the sandbox number once. Sandbox sessions expire after 72h of inactivity; for production, register your own WhatsApp sender in Twilio. |
| `meta` | Production, cheapest at volume | WhatsApp Cloud API. Free-form text only reaches people who messaged your business number in the last 24h. To send any time, create and approve a template with one `{{1}}` body variable and set `META_TEMPLATE_NAME`. |
| `callmebot` | Personal, zero cost | Each recipient registers once with CallMeBot and gets their own API key. Unofficial service with rate limits. |

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
