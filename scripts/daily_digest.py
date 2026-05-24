import os
import time
import random
from datetime import datetime
from google import genai
from google.genai import types
from notion_client import Client

# ── Config ────────────────────────────────────────────────────────────────────
NOTION_TOKEN      = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY")

ARTICLE_COUNT = 3

ALL_CATEGORIES = [
    "Finance", "Economics", "Politics", "Science", "Technology",
    "Health", "Climate", "Culture", "Fashion", "History",
    "Philosophy", "Sports", "Space", "AI & Robotics", "Geopolitics",
]

# ── Safety check ──────────────────────────────────────────────────────────────
if not all([NOTION_TOKEN, NOTION_DATABASE_ID, GEMINI_API_KEY]):
    print("❌ Error: Missing environment variables. Check your GitHub Secrets.")
    exit(1)

# ── Clients ───────────────────────────────────────────────────────────────────
notion = Client(auth=NOTION_TOKEN)
gemini = genai.Client(api_key=GEMINI_API_KEY)   # explicit key — no env-name guessing

# ── Helpers ───────────────────────────────────────────────────────────────────
def today_label():
    return datetime.now().strftime("%-d %B %Y")   # e.g. "24 May 2026"

def pick_categories(n):
    return random.sample(ALL_CATEGORIES, n)

# ── Gemini fetch ──────────────────────────────────────────────────────────────
def fetch_article(category):
    print(f"  Fetching: {category}...")

    prompt = f"""Today is {today_label()}.
Find ONE real, recent news article published in the last 7 days on the topic: '{category}'.
Do NOT invent headlines or sources. Use your knowledge of recent events.

Reply in exactly this format (no extra text, no markdown):

HEADLINE: <headline here>
SOURCE: <publication name and URL>
SUMMARY: <3 sentences summarising the key facts>
WHY_IT_MATTERS: <1 sentence on broader significance>
"""

    try:
        response = gemini.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        return response.text.strip()
    except Exception as e:
        print(f"  ❌ Gemini error for {category}: {e}")
        return None

# ── Notion write ──────────────────────────────────────────────────────────────
def add_to_notion(content, category):
    try:
        headline = f"Daily {category} Update"
        for line in content.split("\n"):
            if line.upper().startswith("HEADLINE:"):
                headline = line.split(":", 1)[1].strip()
                break

        notion.pages.create(
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
        print(f"  ✅ Added to Notion: {headline[:60]}")
    except Exception as e:
        print(f"  ❌ Notion error for {category}: {e}")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    today = today_label()
    categories = pick_categories(ARTICLE_COUNT)

    print(f"[{today}] Starting Daily Digest…")
    print(f"  Categories: {', '.join(categories)}")

    for category in categories:
        content = fetch_article(category)
        if content:
            add_to_notion(content, category)
        time.sleep(60)   # free tier: 15 req/min — wait 60s between calls to be safe

    print("Done!")

if __name__ == "__main__":
    main()