#!/usr/bin/env python3
"""
Witness Statement — Daily AI poetry from the news.
Three models. Same prompt. Same headlines. Different eyes.
"""

import os
import json
import datetime
import urllib.request
import urllib.parse
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


# ── API calls ───────────────────────────────────────────────
def api_post(url, headers, body, timeout=60):
    """Simple POST request, returns parsed JSON."""
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"[error] HTTP {e.code}: {error_body[:500]}")
        return None


def call_gemini(prompt, headlines_text):
    key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={key}"
    body = {
        "contents": [{"parts": [{"text": prompt + "\n\n---\nHEADLINES:\n" + headlines_text}]}],
        "generationConfig": {"temperature": 1.0, "maxOutputTokens": 2048},
    }
    resp = api_post(url, {"Content-Type": "application/json"}, body)
    try:
        return resp["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        print(f"[error] Gemini response: {json.dumps(resp)[:500]}")
        return None


def call_claude(prompt, headlines_text):
    key = os.environ["ANTHROPIC_API_KEY"]
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    }
    body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2048,
        "temperature": 1.0,
        "messages": [
            {"role": "user", "content": prompt + "\n\n---\nHEADLINES:\n" + headlines_text}
        ],
    }
    resp = api_post(url, headers, body)
    try:
        return resp["content"][0]["text"]
    except (KeyError, IndexError):
        print(f"[error] Claude response: {json.dumps(resp)[:500]}")
        return None


def call_gpt(prompt, headlines_text):
    key = os.environ["OPENAI_API_KEY"]
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }
    body = {
        "model": "gpt-5.2",
        "temperature": 1.0,
        "max_completion_tokens": 2048,
        "messages": [
            {"role": "user", "content": prompt + "\n\n---\nHEADLINES:\n" + headlines_text}
        ],
    }
    resp = api_post(url, headers, body)
    try:
        return resp["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        print(f"[error] GPT response: {json.dumps(resp)[:500]}")
        return None


# ── build the post ──────────────────────────────────────────
def create_post(gemini_poem, claude_poem, gpt_poem):
    filename = f"_posts/{DATE}-daily-poems.md"
    os.makedirs("_posts", exist_ok=True)

    content = f"""---
layout: post
title: "{DATE}"
date: {DATE}
---

## Gemini

{gemini_poem or '*[no signal]*'}

## Claude

{claude_poem or '*[no signal]*'}

## GPT

{gpt_poem or '*[no signal]*'}
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

    print("[witness] Calling Gemini...")
    try:
        gemini = call_gemini(PROMPT, headlines_text)
    except Exception as e:
        print(f"[error] Gemini exception: {e}")
        gemini = None
    print(f"[witness] Gemini: {'OK' if gemini else 'FAILED'}")

    print("[witness] Calling Claude...")
    try:
        claude = call_claude(PROMPT, headlines_text)
    except Exception as e:
        print(f"[error] Claude exception: {e}")
        claude = None
    print(f"[witness] Claude: {'OK' if claude else 'FAILED'}")

    print("[witness] Calling GPT...")
    try:
        gpt = call_gpt(PROMPT, headlines_text)
    except Exception as e:
        print(f"[error] GPT exception: {e}")
        gpt = None
    print(f"[witness] GPT: {'OK' if gpt else 'FAILED'}")

    if not any([gemini, claude, gpt]):
        print("[error] All models failed. No post created.")
        exit(1)

    create_post(gemini, claude, gpt)
