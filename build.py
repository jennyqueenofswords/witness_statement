#!/usr/bin/env python3
"""
Build static site from _posts/ markdown files.
Outputs to _site/ for gh-pages deployment.
Replaces Jekyll when Actions is unavailable.
"""

import os
import re
import markdown

SITE_DIR = "_site"
POSTS_DIR = "_posts"
TITLE = "Witness Statement"


def parse_post(filepath):
    """Parse a Jekyll-style markdown post, return (frontmatter, body_html)."""
    with open(filepath) as f:
        text = f.read()

    # Strip YAML front matter
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if m:
        fm_text = m.group(1)
        body = text[m.end():]
    else:
        fm_text = ""
        body = text

    # Parse simple frontmatter
    fm = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip().strip('"')

    body_html = markdown.markdown(body, extensions=["fenced_code"])
    return fm, body_html


def build():
    os.makedirs(SITE_DIR, exist_ok=True)

    # Collect and sort posts (newest first)
    posts = []
    for f in sorted(os.listdir(POSTS_DIR), reverse=True):
        if not f.endswith(".md"):
            continue
        fm, html = parse_post(os.path.join(POSTS_DIR, f))
        posts.append((fm.get("title", f), fm.get("date", ""), html))

    # Build index
    post_sections = []
    for title, date, html in posts:
        post_sections.append(f'<h2>{title}</h2>\n{html}')

    all_posts = "\n".join(post_sections)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{TITLE}</title>
  <style>
    body {{
      font-family: 'Noto Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif;
      font-size: 14px;
      line-height: 1.6;
      color: #222;
      background: #fff;
      margin: 0;
      padding: 0;
    }}
    .container {{
      max-width: 860px;
      margin: 0 auto;
      padding: 20px 40px;
    }}
    h1 {{
      font-size: 28px;
      color: #222;
      margin-bottom: 4px;
    }}
    h1 + p {{
      color: #727272;
      margin-top: 0;
    }}
    h2 {{
      font-size: 20px;
      color: #393939;
      border-bottom: 1px solid #ddd;
      padding-bottom: 6px;
      margin-top: 40px;
    }}
    h3 {{
      font-size: 16px;
      color: #494949;
    }}
    a {{
      color: #267CB9;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    pre {{
      background: #f8f8f8;
      border: 1px solid #ddd;
      padding: 12px;
      overflow-x: auto;
      font-size: 13px;
      line-height: 1.5;
    }}
    code {{
      font-family: 'Courier New', monospace;
      font-size: 13px;
    }}
    em {{
      color: #727272;
    }}
    @media (max-width: 720px) {{
      .container {{ padding: 10px 16px; }}
      pre {{ font-size: 12px; padding: 8px; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <h1>{TITLE}</h1>
    <p>The LLMs are watching. New poems every day at 12pm UTC.</p>
    {all_posts}
  </div>
</body>
</html>"""

    with open(os.path.join(SITE_DIR, "index.html"), "w") as f:
        f.write(page)

    print(f"[build] {len(posts)} posts → {SITE_DIR}/index.html")


if __name__ == "__main__":
    build()
