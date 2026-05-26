import json
import logging
import os
from datetime import date

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

POWER_TAB = "Power Users"
SEEN_TAB = "Seen Users"
SCORE_THRESHOLD = 65

POWER_HEADERS = [
    "Date Added",
    "Username",
    "Score",
    "Verified",
    "Followers",
    "Lifetime Posts (ideas)",
    "Lifetime Likes",
    "Watchlist Count",
    "Tickers Seen (today)",
    "Post Count (in feed today)",
    "Join Date",
    "Name",
    "Profile URL",
]


def _client() -> gspread.Client:
    raw = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
    if not raw:
        raise EnvironmentError("GOOGLE_CREDENTIALS_JSON env var is not set")
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
    return gspread.authorize(creds)


def _open_sheet() -> gspread.Spreadsheet:
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
    if not sheet_id:
        raise EnvironmentError("GOOGLE_SHEET_ID env var is not set")
    return _client().open_by_key(sheet_id)


def _ensure_tabs(sheet: gspread.Spreadsheet) -> tuple[gspread.Worksheet, gspread.Worksheet]:
    existing = {ws.title for ws in sheet.worksheets()}

    if POWER_TAB not in existing:
        pw = sheet.add_worksheet(title=POWER_TAB, rows=10000, cols=len(POWER_HEADERS))
        pw.append_row(POWER_HEADERS, value_input_option="USER_ENTERED")
    else:
        pw = sheet.worksheet(POWER_TAB)

    if SEEN_TAB not in existing:
        sw = sheet.add_worksheet(title=SEEN_TAB, rows=100000, cols=2)
        sw.append_row(["Username", "First Seen"], value_input_option="USER_ENTERED")
    else:
        sw = sheet.worksheet(SEEN_TAB)

    return pw, sw


def get_seen_usernames() -> set[str]:
    sheet = _open_sheet()
    _, sw = _ensure_tabs(sheet)
    values = sw.col_values(1)
    return set(values[1:])  # skip header row


def save_results(users: list[dict]) -> tuple[int, int]:
    """
    Write results to Google Sheets.
    Returns (total_saved, power_users_saved).
    """
    sheet = _open_sheet()
    pw, sw = _ensure_tabs(sheet)

    today = str(date.today())
    power_rows: list[list] = []
    seen_rows: list[list] = []

    for u in users:
        username = u["username"]
        seen_rows.append([username, today])

        if u.get("score", 0) >= SCORE_THRESHOLD:
            tickers_str = ", ".join(sorted(u.get("tickers_seen", set())))
            power_rows.append([
                today,
                username,
                u["score"],
                "Yes" if u.get("verified") else "No",
                u.get("followers", 0),
                u.get("ideas", 0),
                u.get("like_count", 0),
                u.get("watchlist_stocks_count", 0),
                tickers_str,
                u.get("post_count", 0),
                u.get("join_date", ""),
                u.get("name", ""),
                f"https://stocktwits.com/{username}",
            ])

    if power_rows:
        pw.append_rows(power_rows, value_input_option="USER_ENTERED")

    if seen_rows:
        sw.append_rows(seen_rows, value_input_option="USER_ENTERED")

    logger.info(
        "Saved %d seen users and %d power users to Google Sheets",
        len(seen_rows),
        len(power_rows),
    )
    return len(seen_rows), len(power_rows)
