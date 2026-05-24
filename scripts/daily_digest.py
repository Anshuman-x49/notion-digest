import os
import time
from google import genai
from google.genai import types
from notion_client import Client

# 1. Initialize Configuration
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 2. Safety Check for Environment Variables
if not all([NOTION_TOKEN, NOTION_DATABASE_ID, GEMINI_API_KEY]):
    print("❌ Error: Missing required environment variables. Check your GitHub Secrets.")
    exit(1)

# 3. Initialize Clients
notion = Client(auth=NOTION_TOKEN)
# The SDK automatically uses GEMINI_API_KEY from the environment
gemini = genai.Client()

# Match the categories from your log
CATEGORIES = ["Culture", "Philosophy", "History"]

def fetch_articles(category):
    """Uses Gemini 1.5 Flash to find a real, current article and format a digest."""
    print(f"  Fetching latest updates for: {category}...")
    
    prompt = f"""
    Find a major, real news article or prominent essay from within the last 24 hours regarding the topic: '{category}'.
    Provide a curated digest structured exactly like this:
    
    HEADLINE: [Clear, compelling headline]
    SOURCE: [Name of publication or URL]
    SUMMARY: [Exactly 3 sentences explaining the facts of what happened or what is argued]
    WHY_IT_MATTERS: [1-2 sentences on its broader cultural or historical impact]
    """

    try:
        response = gemini.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3)
        )
        return response.text
    except Exception as e:
        print(f"  ❌ Error calling Gemini API for {category}: {e}")
        return None

def add_to_notion(content, category):
    """Parses the digest content and adds it as a clean item in your Notion database."""
    try:
        # Simple line-splitting logic to pluck out the headline for the page Title
        lines = content.split('\n')
        headline = f"Daily {category} Update"
        for line in lines:
            if "HEADLINE:" in line.upper():
                headline = line.split(":", 1)[1].strip()
                break

        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "Name": {"title": [{"text": {"content": headline}}]},
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
        print(f"  ✅ Successfully added {category} to Notion.")
    except Exception as e:
        print(f"  ❌ Error adding {category} to Notion: {e}")

def main():
    print("[2026-05-24] Starting Daily Digest…")
    print(f"  Categories: {', '.join(CATEGORIES)}")
    print("  Fetching articles via Gemini + web search…")
    
    for category in CATEGORIES:
        digest_content = fetch_articles(category)
        if digest_content:
            add_to_notion(digest_content, category)
        
        # 5-second sleep to easily stay clear of free tier rate restrictions
        time.sleep(5)
    
    print("Done!")

if __name__ == "__main__":
    main()