import os
import time
import random
from datetime import datetime
from groq import Groq
from notion_client import Client
from notion_client.errors import APIResponseError

# ── Config ────────────────────────────────────────────────────────────────────
NOTION_TOKEN       = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
GROQ_API_KEY       = os.environ.get("GROQ_API_KEY")

ARTICLE_COUNT = 3

ALL_CATEGORIES = [
    "Finance", "Economics", "Politics", "Science", "Technology",
    "Health", "Climate", "Culture", "Fashion", "History",
    "Philosophy", "Sports", "Space", "AI & Robotics", "Geopolitics",
]

# ── Safety check ──────────────────────────────────────────────────────────────
if not all([NOTION_TOKEN, NOTION_DATABASE_ID, GROQ_API_KEY]):
    print("❌ Error: Missing environment variables. Check your GitHub Secrets.")
    exit(1)

# ── Clients ───────────────────────────────────────────────────────────────────
notion = Client(auth=NOTION_TOKEN)
groq   = Groq(api_key=GROQ_API_KEY)

# ── Helpers ───────────────────────────────────────────────────────────────────
def today_label():
    return datetime.now().strftime("%-d %B %Y")

def today_iso():
    return datetime.now().strftime("%Y-%m-%d")

def pick_categories(n):
    return random.sample(ALL_CATEGORIES, n)

def parse_field(content, field):
    """Extract a field value from the formatted response."""
    for line in content.split("\n"):
        if line.upper().startswith(f"{field.upper()}:"):
            return line.split(":", 1)[1].strip()
    return ""

# ── Groq fetch ────────────────────────────────────────────────────────────────
def fetch_article(category):
    print(f"  Fetching: {category}...")
    prompt = f"""Today is {today_label()}.
Find ONE real, recent news article published in the last 7 days on the topic: '{category}'.
Do NOT invent headlines or sources.

Reply in exactly this format (no extra text, no markdown):

HEADLINE: <headline here>
SOURCE_NAME: <publication name only>
SOURCE_URL: <full URL only>
SUMMARY: <3 sentences summarising the key facts>
WHY_IT_MATTERS: <1 sentence on broader significance>
"""
    try:
        response = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        text = response.choices[0].message.content.strip()
        print(f"  ✅ Groq responded for {category}")
        return text
    except Exception as e:
        print(f"  ❌ Groq error for {category}: {e}")
        return None

# ── Notion write ──────────────────────────────────────────────────────────────
def add_to_notion(content, category):
    headline     = parse_field(content, "HEADLINE") or f"Daily {category} Update"
    source_name  = parse_field(content, "SOURCE_NAME") or "Source"
    source_url   = parse_field(content, "SOURCE_URL") or ""
    summary      = parse_field(content, "SUMMARY") or ""
    why_matters  = parse_field(content, "WHY_IT_MATTERS") or ""

    print(f"  Sending to Notion: {headline[:60]}")

    # Build page children blocks — source link at the top as a clickable link
    children = []

    # 1. Source link block at the top
    if source_url:
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": source_name,
                            "link": {"url": source_url}
                        },
                        "annotations": {"bold": True, "color": "blue"}
                    }
                ]
            }
        })

    # 2. Divider
    children.append({"object": "block", "type": "divider", "divider": {}})

    # 3. Summary heading + text
    children.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {"rich_text": [{"type": "text", "text": {"content": "Summary"}}]}
    })
    children.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": summary}}]}
    })

    # 4. Why it matters heading + text
    children.append({
        "object": "block",
        "type": "heading_3",
        "heading_3": {"rich_text": [{"type": "text", "text": {"content": "Why It Matters"}}]}
    })
    children.append({
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": why_matters}}]}
    })

    try:
        response = notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Name":     {"title":  [{"text": {"content": headline}}]},
                "Category": {"select": {"name": category}},
                "Date":     {"date":   {"start": today_iso()}},
            },
            children=children,
        )
        print(f"  ✅ Added to Notion! Page ID: {response['id']}")
    except APIResponseError as e:
        print(f"  ❌ Notion error: {e}")
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    categories = pick_categories(ARTICLE_COUNT)

    print(f"[{today_iso()}] Starting Daily Digest…")
    print(f"  Categories: {', '.join(categories)}")

    for i, category in enumerate(categories):
        content = fetch_article(category)
        if content:
            add_to_notion(content, category)
        if i < len(categories) - 1:
            time.sleep(2)

    print("Done!")

if __name__ == "__main__":
    main()