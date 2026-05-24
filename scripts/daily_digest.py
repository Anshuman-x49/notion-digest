import anthropic
import json
import os
import random
import re
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
NOTION_PAGE_ID = "36aae6c3e63c807482e1ff8840983b8a"   # Your Articles page ID
ARTICLE_COUNT  = 3

ALL_CATEGORIES = [
    "Finance", "Economics", "Politics", "Science", "Technology",
    "Health", "Climate", "Culture", "Fashion", "History",
    "Philosophy", "Sports", "Space", "AI & Robotics", "Geopolitics",
]

CATEGORY_ICONS = {
    "Finance":      "💰", "Economics":  "📊", "Politics":    "🏛️",
    "Science":      "⚗️", "Technology": "💻", "Health":      "🩺",
    "Climate":      "🌍", "Culture":    "🎭", "Fashion":     "👗",
    "History":      "📜", "Philosophy": "🧠", "Sports":      "⚽",
    "Space":        "🚀", "AI & Robotics": "🤖", "Geopolitics": "🌐",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def pick_categories(n: int) -> list[str]:
    return random.sample(ALL_CATEGORIES, n)


def today_label() -> str:
    return datetime.now().strftime("%-d %B %Y")   # e.g. "24 May 2026"


def today_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")


# ── Claude: research + write articles ────────────────────────────────────────

def fetch_articles(categories: list[str]) -> list[dict]:
    """Ask Claude (with web search) to find one real article per category."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    system = """You are a research assistant. For each category given, find ONE
genuinely recent, well-sourced news article published in the last 7 days.
Use the web_search tool to find real articles — do not invent headlines or URLs.

Return ONLY a JSON array (no markdown fences, no extra text) with this shape:
[
  {
    "category": "...",
    "headline": "...",
    "summary": "3-sentence summary of key points.",
    "source_name": "Publication name",
    "source_url": "https://...",
    "why_it_matters": "One sentence."
  }
]"""

    user = (
        f"Today is {today_label()}. Find one recent article for each of these "
        f"categories: {', '.join(categories)}. Return the JSON array only."
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        system=system,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": user}],
    )

    # Extract the final text block (after tool use)
    text = ""
    for block in response.content:
        if block.type == "text":
            text = block.text

    # Strip accidental markdown fences
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("```").strip()

    return json.loads(text)


# ── Notion helpers ────────────────────────────────────────────────────────────

def notion_request(method: str, path: str, body: dict | None = None) -> dict:
    import urllib.request

    token = os.environ["NOTION_TOKEN"]
    url   = f"https://api.notion.com/v1{path}"
    data  = json.dumps(body).encode() if body else None

    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization",  f"Bearer {token}")
    req.add_header("Notion-Version", "2022-06-28")
    req.add_header("Content-Type",   "application/json")

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def create_page(parent_id: str, title: str, icon: str, content: str) -> str:
    """Create a Notion page and return its ID."""
    body = {
        "parent": {"page_id": parent_id},
        "icon":   {"type": "emoji", "emoji": icon},
        "properties": {
            "title": {"title": [{"text": {"content": title}}]}
        },
        "children": [
            {
                "object": "block",
                "type":   "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                },
            }
        ],
    }
    result = notion_request("POST", "/pages", body)
    return result["id"]


def build_article_content(article: dict) -> str:
    return (
        f"Category: {article['category']}\n"
        f"Date: {today_label()}\n"
        f"Source: {article['source_name']} — {article['source_url']}\n\n"
        f"Summary\n\n{article['summary']}\n\n"
        f"Why It Matters\n\n{article['why_it_matters']}"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"[{today_iso()}] Starting Daily Digest…")

    categories = pick_categories(ARTICLE_COUNT)
    print(f"  Categories: {', '.join(categories)}")

    print("  Fetching articles via Claude + web search…")
    articles = fetch_articles(categories)
    print(f"  Got {len(articles)} articles")

    # Create parent "Daily Digest — DD Month YYYY" page
    digest_title = f"Daily Digest — {today_label()}"
    digest_id = create_page(
        parent_id=NOTION_PAGE_ID,
        title=digest_title,
        icon="📰",
        content=f"Today's digest across {', '.join(categories)}.",
    )
    print(f"  Created parent page: {digest_title}")

    # Create one child page per article
    for article in articles:
        icon = CATEGORY_ICONS.get(article["category"], "📄")
        create_page(
            parent_id=digest_id,
            title=article["headline"],
            icon=icon,
            content=build_article_content(article),
        )
        print(f"  ✓ {article['category']}: {article['headline'][:60]}…")

    print("  Done!")


if __name__ == "__main__":
    main()
