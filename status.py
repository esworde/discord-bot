#!/usr/bin/env python3
"""Post every status-page incident update (opened, each update, resolved) to a Discord channel webhook.
Prints instead if DISCORD_WEBHOOK is unset."""
import json
import os
import re
import urllib.request
from pathlib import Path

# Any Atlassian Statuspage or incident.io status page works here (both serve /api/v2/incidents.json).
PAGES = {
    "Anthropic": "https://status.anthropic.com",
    "OpenAI": "https://status.openai.com",
    "E2B": "https://status.e2b.dev",
}
SEEN = Path(__file__).with_name("seen.json")
WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
EMOJI = {"investigating": "🔴", "identified": "🟠", "monitoring": "🟡", "resolved": "🟢", "postmortem": "📝"}


def request(url, data=None):
    headers = {"User-Agent": "status-bot", "Content-Type": "application/json"}
    with urllib.request.urlopen(urllib.request.Request(url, data, headers), timeout=20) as r:
        return r.read().decode()


# Each source yields (update id, incident title, status, message, link), oldest first.

def statuspage(base):
    for inc in reversed(json.loads(request(f"{base}/api/v2/incidents.json"))["incidents"]):
        for u in reversed(inc["incident_updates"]):
            yield u["id"], inc["name"], u["status"], u["body"], f"{base}/incidents/{inc['id']}"


def openrouter():
    # Datadog status page: feed is disabled, but the page's own data file has every update
    base = "https://status.openrouter.ai"
    for inc in reversed(json.loads(request(f"{base}/config.json"))["incidents"]):
        for u in reversed(inc["timeline"]):
            yield u["id"], inc["title"], u["status"], u["description"], f"{base}/incidents/{inc['id']}"


def railway():
    # ponytail: no feed or API, so this regexes the incident data embedded in their homepage; breaks if they change it
    base = "https://status.railway.com"
    for chunk in reversed(request(base).split('slug:"')[1:]):
        incident = re.match(r'([A-Z0-9]+)",title:"((?:[^"\\]|\\.)*)"', chunk)
        updates = re.findall(r'\{id:"([^"]+)",status:"(\w+)",message:"((?:[^"\\]|\\.)*)"', chunk)
        for uid, status, message in reversed(updates if incident else []):
            yield uid, js(incident[2]), status.lower(), js(message), f"{base}/incident/{incident[1]}"


def js(literal):
    try:
        return json.loads(f'"{literal}"')
    except ValueError:
        return literal


def post(msg):
    if WEBHOOK:
        request(WEBHOOK, json.dumps({"content": msg[:2000]}).encode())
    else:
        print(msg)


def main():
    seen = json.loads(SEEN.read_text()) if SEEN.exists() else {}
    sources = {name: lambda base=base: statuspage(base) for name, base in PAGES.items()}
    sources |= {"OpenRouter": openrouter, "Railway": railway}
    for name, source in sources.items():
        seeding = name not in seen  # new source: record its history silently instead of posting all of it
        prev = set(seen.get(name, []))
        try:
            updates = list(source())
        except Exception as e:  # one broken status page shouldn't block the others
            print(f"{name} failed: {e}")
            continue
        done = {key: 1 for key, *_ in updates if key in prev}  # also forgets ids that dropped off the page
        try:
            for key, title, status, message, link in updates:
                if key not in done:
                    if not seeding:
                        post(f"{EMOJI.get(status, '🔴')} **{name}** · {title}\n**{status.title()}** - {message[:1500]}\n<{link}>")
                    done[key] = 1
        except Exception as e:  # Discord hiccup: what got posted is saved, the rest retries next run
            print(f"{name} post failed: {e}")
        seen[name] = list(done)
    SEEN.write_text(json.dumps(seen, indent=1) + "\n")


if __name__ == "__main__":
    main()
