# Daily Notion Digest

Automatically adds 3 curated news articles to your Notion every day at **8:00 AM IST**, using Claude (with live web search) to find real, current stories across random categories.

---

## Setup (5 minutes)

### 1 — Create a GitHub repo

Go to github.com → **New repository** → name it `notion-digest` → **Create**.

### 2 — Upload these files

Upload the two files maintaining this structure:
```
.github/
  workflows/
    daily_digest.yml
scripts/
  daily_digest.py
```

### 3 — Get your API keys

**Anthropic API key**
1. Go to https://console.anthropic.com
2. API Keys → Create Key
3. Copy the key (starts with `sk-ant-…`)

**Notion integration token**
1. Go to https://www.notion.so/profile/integrations
2. Click **New integration** → give it a name (e.g. "Daily Digest")
3. Copy the **Internal Integration Secret** (starts with `ntn_…` or `secret_…`)
4. Open your Notion **Articles** page → `···` menu → **Connections** → add your integration

### 4 — Add secrets to GitHub

In your repo: **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|------|-------|
| `ANTHROPIC_API_KEY` | Your Anthropic key |
| `NOTION_TOKEN` | Your Notion integration token |

### 5 — Test it manually

Go to **Actions** tab → **Daily Notion Digest** → **Run workflow** → **Run workflow**.

Check your Notion — a new "Daily Digest — DD Month YYYY" page should appear under Articles within ~30 seconds.

---

## Customise

Open `scripts/daily_digest.py` and edit the top of the file:

```python
ARTICLE_COUNT  = 3          # how many articles per day
ALL_CATEGORIES = [...]      # add/remove categories you want
```

To change the time, edit the cron line in `.github/workflows/daily_digest.yml`:
```yaml
- cron: "30 2 * * *"   # 2:30 UTC = 8:00 AM IST
```
Use https://crontab.guru to convert your timezone.

---

## How it works

1. GitHub Actions wakes up at 2:30 AM UTC (8 AM IST)
2. Picks N random categories from your list
3. Calls Claude with web search enabled — Claude finds real, recent articles
4. Creates a dated parent page in Notion, then one child page per article
