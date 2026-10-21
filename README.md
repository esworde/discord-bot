# status-bot

Posts every incident update (opened, each update, resolved) from status pages to a Discord channel. No bot, no server: a GitHub Actions cron runs `status.py` every 5 minutes and posts to a Discord webhook.

Watches Anthropic, OpenAI, E2B, OpenRouter and Railway.

🔴 investigating · 🟠 identified · 🟡 monitoring · 🟢 resolved

## Setup

1. Discord: channel settings → Integrations → Webhooks → New Webhook → Copy Webhook URL.
2. GitHub: repo Settings → Secrets and variables → Actions → New repository secret, name `DISCORD_WEBHOOK`, value = that URL.
3. Actions tab → `status` → Run workflow. The first run records existing incidents silently; after that every new update is posted.

Local dry run (prints instead of posting): `python3 status.py`

## Adding a page

Add one line to `PAGES` in `status.py` with the status page's base URL. Any Atlassian Statuspage or incident.io page works (check that `<url>/api/v2/incidents.json` loads), e.g.:

```python
"GitHub": "https://www.githubstatus.com",
"Vercel": "https://www.vercel-status.com",
"Cloudflare": "https://www.cloudflarestatus.com",
"Supabase": "https://status.supabase.com",
"Cursor": "https://status.cursor.com",
```

OpenRouter (Datadog) and Railway (custom) don't serve that API, so they have their own small functions.
