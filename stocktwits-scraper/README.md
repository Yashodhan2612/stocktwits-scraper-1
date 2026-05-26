# StockTwits Daily Power-User Scraper

A GitHub Actions cron job that runs every day, discovers active StockTwits users from 50 configured tickers, scores them 1–100 for fit as StockDashboard power users, and writes anyone scoring **≥ 65** to a Google Sheet.

**100% free.** Uses only:
- StockTwits public API (no API key required)
- Google Sheets (free tier)
- GitHub Actions (free for public repos)

---

## How it works

1. Fetches the 30 most recent posts for each of 50 stock tickers using the StockTwits public API.
2. Extracts every unique user who posted and aggregates their activity across all tickers.
3. Filters out users already seen in previous runs (stored in "Seen Users" tab).
4. Takes the top 100 fresh users ranked by ticker breadth and follower count.
5. Scores each user 1–100 (details below).
6. Writes users scoring ≥ 65 to the **Power Users** tab in Google Sheets.

---

## Scoring formula

| Dimension | Max pts | Signal |
|---|---|---|
| Ticker breadth (today's feed) | 20 | Distinct tickers they posted about across all 50 streams today |
| Lifetime posts (`ideas`) | 25 | Total posts ever on StockTwits — activity depth |
| Follower count | 25 | Reach / social influence proxy |
| Lifetime likes (`like_count`) | 15 | Historical quality signal — how much their posts are liked |
| Watchlist diversity | 10 | Number of stocks they actively watch — proxy for research depth |
| Verified account | 5 | StockTwits official/verified badge |
| **Total** | **100** | |

> The StockTwits public API does not return per-message likes/replies counts, so scoring uses lifetime user stats embedded in every message's user object instead.

**≥ 65 = potential StockDashboard power user.**

---

## Setup

### Step 1 — Google Cloud: create a service account

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a new project (or use an existing one).
2. In the left sidebar → **APIs & Services → Library**.
3. Search for **Google Sheets API** → click it → **Enable**.
4. Search for **Google Drive API** → click it → **Enable**.
5. Go to **APIs & Services → Credentials** → **+ Create Credentials → Service account**.
6. Give it any name (e.g. `stocktwits-scraper`) → **Create and Continue** → skip optional steps → **Done**.
7. Click the service account you just created → **Keys** tab → **Add Key → Create new key → JSON**.
8. A `credentials.json` file downloads automatically. **Keep this safe — do not commit it.**
9. Copy the `client_email` value from that file (looks like `name@project.iam.gserviceaccount.com`).

### Step 2 — Google Sheets: create the spreadsheet

1. Go to [Google Sheets](https://sheets.google.com) → **Blank spreadsheet**.
2. Rename it to anything you like (e.g. `StockTwits Power Users`).
3. Click **Share** (top-right) → paste the `client_email` from Step 1 → set role to **Editor** → **Send**.
4. Copy the spreadsheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit
   ```

The scraper will automatically create two tabs on first run:
- **Power Users** — users scoring ≥ 65 with full details.
- **Seen Users** — all processed usernames (for daily deduplication).

### Step 3 — GitHub: fork or create the repository

1. Push this project to a **public** GitHub repository (public repos get free unlimited Actions minutes).
2. In your repo → **Settings → Secrets and variables → Actions → New repository secret**.

   Add these two secrets:

   | Secret name | Value |
   |---|---|
   | `GOOGLE_CREDENTIALS_JSON` | The **entire contents** of the `credentials.json` file downloaded in Step 1 (paste as-is, including the curly braces) |
   | `GOOGLE_SHEET_ID` | The spreadsheet ID you copied in Step 2 |

### Step 4 — Verify the workflow

1. In your repo → **Actions** tab.
2. Click **Daily StockTwits Scraper** → **Run workflow** → **Run workflow** (to trigger a manual test run).
3. Watch the logs. After ~3–4 minutes you should see output like:
   ```
   Unique users found across all streams: 842
   Fresh (unseen) users after dedup: 842
   Selected top 100 users to score
   Done. 34/100 users scored ≥65 (power users). 34 written to sheet.
   ```
4. Open your Google Sheet — you should see data in the **Power Users** tab.

From now on the scraper runs automatically every day at **10:00 AM ET**.

---

## Running locally

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/stocktwits-scraper.git
cd stocktwits-scraper

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GOOGLE_CREDENTIALS_JSON='{"type":"service_account",...}'  # contents of credentials.json
export GOOGLE_SHEET_ID='your_sheet_id_here'

# Run
python -m scraper.main
```

---

## Customization

### Change the ticker list
Edit [`config/tickers.py`](config/tickers.py). Add or remove any tickers — the scraper uses all of them.

### Change the daily user target
In [`scraper/main.py`](scraper/main.py), change the `DAILY_TARGET` constant:
```python
DAILY_TARGET = 100  # change to any number
```

### Change the score threshold
In [`scraper/storage.py`](scraper/storage.py), change `SCORE_THRESHOLD`:
```python
SCORE_THRESHOLD = 65  # lower to capture more, raise to be more selective
```

### Change the run time
In [`.github/workflows/daily_scraper.yml`](.github/workflows/daily_scraper.yml), edit the cron expression:
```yaml
- cron: '0 14 * * *'  # 14:00 UTC = 10:00 AM ET
```
Use [crontab.guru](https://crontab.guru) to generate any schedule you want.

---

## Google Sheet columns

| Column | Description |
|---|---|
| Date Added | Date this user was first scored |
| Username | StockTwits handle |
| Score | Power-user score (1–100) |
| Verified | Whether they have a StockTwits official/verified badge |
| Followers | Follower count at time of scrape |
| Lifetime Posts (ideas) | Total posts ever published on StockTwits |
| Lifetime Likes | Total likes received on all their posts ever |
| Watchlist Count | Number of stocks they actively watch |
| Tickers Seen (today) | Comma-separated list of tickers they posted about today |
| Post Count (in feed today) | Number of posts seen across today's ticker streams |
| Join Date | When they joined StockTwits |
| Name | Display name on StockTwits |
| Profile URL | Direct link to their StockTwits profile |

---

## Rate limits & API access

StockTwits public API allows ~200 requests per hour without authentication.

This scraper makes at most **50 requests per run** (one per ticker), with a 1.5-second delay between each. A full run takes roughly 2–3 minutes and uses only 25% of the hourly budget.

> **Note:** StockTwits is not currently accepting new API key registrations. This scraper works entirely with public, unauthenticated endpoints that remain available.

---

## Project structure

```
stocktwits-scraper/
├── .github/workflows/
│   └── daily_scraper.yml   # GitHub Actions cron job
├── config/
│   └── tickers.py          # Your 50 stock tickers
├── scraper/
│   ├── api.py              # StockTwits API client
│   ├── scorer.py           # 1–100 scoring formula
│   ├── storage.py          # Google Sheets read/write
│   └── main.py             # Orchestration
├── requirements.txt
└── README.md
```
