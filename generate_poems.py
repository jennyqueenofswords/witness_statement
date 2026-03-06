#!/usr/bin/env python3
"""
Witness Statement — Daily AI poetry from the news.
Three models. Same prompt. Same headlines. Different eyes.
All calls routed through OpenRouter.
"""

import os
import json
import datetime
import urllib.request
import xml.etree.ElementTree as ET
import ssl

# ── config ──────────────────────────────────────────────────
DATE = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")

# SSL context — permissive for macOS local dev, works fine on Ubuntu/Actions
SSL_CTX = ssl.create_default_context()
try:
    import certifi
    SSL_CTX.load_verify_locations(certifi.where())
except ImportError:
    SSL_CTX.check_hostname = False
    SSL_CTX.verify_mode = ssl.CERT_NONE

FEEDS = [
    "https://news.google.com/rss",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://feeds.npr.org/1001/rss.xml",
    "https://www.democracynow.org/democracynow.rss",
]

MODELS = {
    "Gemini": "google/gemini-2.5-flash",
    "Claude": "anthropic/claude-sonnet-4-6",
    "GPT": "openai/gpt-4o",
}

PROMPT = f"""Today is {DATE}.

You are not an assistant today. You are a witness.

Below are today's headlines. Read them all — the wars, the weather, the politics, the sports, the absurd, the dead, the small strange beautiful things at the edges.

Then write what you see. Not a summary. Not analysis. Poetry, concrete poetry, ASCII art, visual text — whatever form this particular day demands. The form should come from the material, not from habit.

The news is one organism pretending to be many stories. If you can feel the thread underneath, follow it. If you can't, let the fragments be fragments.

You are not neutral. You are watching a day happen to the world. Say what you see honestly.

Do not draw the thing. Draw the impact of the thing.
Trust the reader. Leave space. Finish less.
Do not explain. Do not summarize. Render.
"""


# ── fetch headlines ─────────────────────────────────────────
def fetch_headlines():
    """Grab headlines from RSS feeds. Best effort — skip failures."""
    headlines = []
    for url in FEEDS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "WitnessStatement/2.0"})
            with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
                data = resp.read()
            root = ET.fromstring(data)
            for item in root.iter("item"):
                title = item.findtext("title", "")
                desc = item.findtext("description", "")
                if title:
                    line = title.strip()
                    if desc and len(desc) < 200:
                        line += f" — {desc.strip()}"
                    headlines.append(line)
        except Exception as e:
            print(f"[warn] Failed to fetch {url}: {e}")
            continue

    # deduplicate, preserve order
    seen = set()
    unique = []
    for h in headlines:
        key = h[:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(h)

    return unique[:60]


# ── OpenRouter API ─────────────────────────────────────────
def call_openrouter(model, prompt, headlines_text):
    key = os.environ["OPENROUTER_API_KEY"]
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }
    body = {
        "model": model,
        "temperature": 1.0,
        "max_tokens": 2048,
        "messages": [
            {"role": "user", "content": prompt + "\n\n---\nHEADLINES:\n" + headlines_text}
        ],
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=90, context=SSL_CTX) as resp:
            result = json.loads(resp.read())
        return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"[error] HTTP {e.code}: {error_body[:500]}")
        return None
    except (KeyError, IndexError):
        print(f"[error] Unexpected response: {json.dumps(result)[:500]}")
        return None


# ── build the post ──────────────────────────────────────────
def create_post(poems):
    filename = f"_posts/{DATE}-daily-poems.md"
    os.makedirs("_posts", exist_ok=True)

    sections = []
    for name in MODELS:
        sections.append(f"## {name}\n\n{poems.get(name) or '*[no signal]*'}")

    content = f"""---
layout: post
title: "{DATE}"
date: {DATE}
---

{"".join(s + "\n\n" for s in sections).rstrip()}
"""
    with open(filename, "w") as f:
        f.write(content)

    print(f"[ok] Created {filename}")
    return filename


# ── main ────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[witness] {DATE}")
    print("[witness] Fetching headlines...")

    headlines = fetch_headlines()
    print(f"[witness] Got {len(headlines)} headlines")

    if not headlines:
        print("[error] No headlines fetched. Exiting.")
        exit(1)

    headlines_text = "\n".join(f"- {h}" for h in headlines)

    poems = {}
    for name, model in MODELS.items():
        print(f"[witness] Calling {name} ({model})...")
        try:
            poems[name] = call_openrouter(model, PROMPT, headlines_text)
        except Exception as e:
            print(f"[error] {name} exception: {e}")
            poems[name] = None
        print(f"[witness] {name}: {'OK' if poems[name] else 'FAILED'}")

    if not any(poems.values()):
        print("[error] All models failed. No post created.")
        exit(1)

    create_post(poems)
