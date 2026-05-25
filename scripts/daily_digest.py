import os
import time
import random
from datetime import datetime
from groq import Groq
from notion_client import Client

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

def pick_categories(n):
    return random.sample(ALL_CATEGORIES, n)

# ── Groq fetch ────────────────────────────────────────────────────────────────
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
        response = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  ❌ Groq error for {category}: {e}")
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
        print(f"  ✅ Added: {headline[:70]}")
    except Exception as e:
        print(f"  ❌ Notion error for {category}: {e}")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    today = today_label()
    categories = pick_categories(ARTICLE_COUNT)

    print(f"[{today}] Starting Daily Digest…")
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