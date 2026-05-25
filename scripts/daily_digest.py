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

# ── Groq fetch ────────────────────────────────────────────────────────────────
def fetch_article(category):
    print(f"  Fetching: {category}...")
    prompt = f"""Today is {today_label()}.
Find ONE real, recent news article published in the last 7 days on the topic: '{category}'.
Do NOT invent headlines or sources.

Reply in exactly this format (no extra text, no markdown):

HEADLINE: <headline here>
SOURCE: <publication name and URL>
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
    headline = f"Daily {category} Update"
    for line in content.split("\n"):
        if line.upper().startswith("HEADLINE:"):
            headline = line.split(":", 1)[1].strip()
            break

    print(f"  Sending to Notion: {headline[:60]}")
    print(f"  Database ID: {NOTION_DATABASE_ID}")

    try:
        # First try with Date property
        response = notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Name":     {"title":  [{"text": {"content": headline}}]},
                "Category": {"select": {"name": category}},
                "Date":     {"date":   {"start": today_iso()}},
            },
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    },
                }
            ],
        )
        print(f"  ✅ Added to Notion! Page ID: {response['id']}")

    except APIResponseError as e:
        print(f"  ⚠️ Notion API error (trying without Date): {e}")
        # Retry without Date property in case it doesn't exist in the DB
        try:
            response = notion.pages.create(
                parent={"database_id": NOTION_DATABASE_ID},
                properties={
                    "Name":     {"title":  [{"text": {"content": headline}}]},
                    "Category": {"select": {"name": category}},
                },
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": content}}]
                        },
                    }
                ],
            )
            print(f"  ✅ Added to Notion (without Date)! Page ID: {response['id']}")
        except APIResponseError as e2:
            print(f"  ❌ Notion failed completely: {e2}")

    except Exception as e:
        print(f"  ❌ Unexpected Notion error: {e}")

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