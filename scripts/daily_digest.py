import os
import time
from google import genai
from notion_client import Client

# 1. Configuration & API Clients
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

notion = Client(auth=NOTION_TOKEN)
gemini = genai.Client(api_key=GEMINI_API_KEY)

CATEGORIES = ["Finance", "Economics", "Politics", "Fashion", "Science"]

def fetch_and_summarize(category):
    """Uses Gemini to 'search' (via its internal knowledge/tools) and format the digest."""
    print(f"--- Processing {category} ---")
    
    prompt = f"""
    Find a major, real news article from within the last 24 hours regarding {category}.
    Provide a digest in the following strict format:
    
    HEADLINE: [Title of the article]
    SOURCE: [Source name and URL if available]
    SUMMARY: [Exactly 3 sentences explaining what happened]
    WHY_IT_MATTERS: [1-2 sentences on the broader impact]
    """

    try:
        # Using gemini-1.5-flash for speed and cost-efficiency
        response = gemini.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"Error fetching {category} from Gemini: {e}")
        return None

def add_to_notion(content, category):
    """Parses the LLM text and creates a new page in your Notion database."""
    try:
        # Simple parsing logic (splitting by the labels in the prompt)
        lines = content.split('\n')
        headline = "Daily Update"
        for line in lines:
            if "HEADLINE:" in line:
                headline = line.replace("HEADLINE:", "").strip()
                break

        notion.pages.create(
            parent={"database_id": DATABASE_ID},
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
        print(f"Successfully added {category} to Notion.")
    except Exception as e:
        print(f"Error adding to Notion: {e}")

def main():
    if not all([NOTION_TOKEN, GEMINI_API_KEY, DATABASE_ID]):
        print("Missing Environment Variables. Check your GitHub Secrets.")
        return

    for cat in CATEGORIES:
        article_data = fetch_and_summarize(cat)
        if article_data:
            add_to_notion(article_data, cat)
        
        # Small delay to respect free-tier rate limits (15 RPM)
        time.sleep(5)

if __name__ == "__main__":
    main()