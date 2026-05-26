"""
Daily StockTwits scraper — entry point.

Flow:
  1. Load already-seen usernames from Google Sheets (dedup guard).
  2. Fetch the stream for each of the 50 configured tickers (50 API calls).
  3. Aggregate lifetime user stats from every message across all streams.
  4. Filter out previously seen users.
  5. Rank candidates by ticker breadth + follower count; take top 100.
  6. Score each candidate (1–100).
  7. Write all 100 to "Seen Users" tab; write ≥65 scorers to "Power Users" tab.

Note: the StockTwits public API does NOT return per-message likes/replies.
Scoring uses lifetime user stats (ideas, like_count, watchlist_stocks_count)
embedded in each user object.
"""

import logging
import sys

from config.tickers import TICKERS
from scraper.api import fetch_symbol_stream
from scraper.scorer import score_user
from scraper.storage import get_seen_usernames, save_results

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

DAILY_TARGET = 100


def _is_verified(user_obj: dict) -> bool:
    return (
        bool(user_obj.get("official"))
        or user_obj.get("identity", "") == "Official"
    )


def _aggregate(messages: list[dict], ticker: str, bucket: dict) -> None:
    """Merge messages from one ticker stream into the running user bucket."""
    for msg in messages:
        user_obj = msg.get("user")
        if not user_obj:
            continue
        username = user_obj.get("username")
        if not username:
            continue

        if username not in bucket:
            bucket[username] = {
                "username": username,
                "name": user_obj.get("name", ""),
                # Lifetime stats — use the latest values seen (they don't change
                # within a run, but we overwrite to keep the freshest snapshot).
                "followers": user_obj.get("followers", 0) or 0,
                "following": user_obj.get("following", 0) or 0,
                "ideas": user_obj.get("ideas", 0) or 0,
                "like_count": user_obj.get("like_count", 0) or 0,
                "watchlist_stocks_count": user_obj.get("watchlist_stocks_count", 0) or 0,
                "join_date": user_obj.get("join_date", ""),
                "verified": _is_verified(user_obj),
                # Today's activity
                "tickers_seen": set(),
                "post_count": 0,
            }
        else:
            # Refresh lifetime stats with latest values
            entry = bucket[username]
            entry["followers"] = user_obj.get("followers", 0) or entry["followers"]
            entry["like_count"] = user_obj.get("like_count", 0) or entry["like_count"]
            entry["ideas"] = user_obj.get("ideas", 0) or entry["ideas"]
            entry["watchlist_stocks_count"] = (
                user_obj.get("watchlist_stocks_count", 0) or entry["watchlist_stocks_count"]
            )

        entry = bucket[username]
        entry["post_count"] += 1
        entry["tickers_seen"].add(ticker)

        # Also capture any additional symbols tagged in the post body
        for sym in msg.get("symbols", []):
            s = sym.get("symbol")
            if s:
                entry["tickers_seen"].add(s)


def run() -> None:
    logger.info("=== StockTwits daily scraper starting ===")

    # Step 1: Deduplication guard
    try:
        seen = get_seen_usernames()
        logger.info("Loaded %d previously seen usernames", len(seen))
    except Exception as exc:
        logger.error("Could not load seen users (%s); proceeding without dedup", exc)
        seen = set()

    # Steps 2 & 3: Fetch ticker streams and aggregate user data
    bucket: dict[str, dict] = {}
    for ticker in TICKERS:
        logger.info("Fetching $%s ...", ticker)
        messages = fetch_symbol_stream(ticker)
        logger.info("  → %d messages", len(messages))
        _aggregate(messages, ticker, bucket)

    logger.info("Unique users found across all streams: %d", len(bucket))

    # Step 4: Remove previously seen users
    fresh = {u: d for u, d in bucket.items() if u not in seen}
    logger.info("Fresh (unseen) users after dedup: %d", len(fresh))

    if not fresh:
        logger.warning("No new users found today — nothing to save.")
        return

    # Step 5: Rank by quality signal; take top DAILY_TARGET
    ranked = sorted(
        fresh.values(),
        key=lambda u: (len(u["tickers_seen"]), u["followers"], u["ideas"]),
        reverse=True,
    )
    selected = ranked[:DAILY_TARGET]
    logger.info("Selected top %d users to score", len(selected))

    # Step 6: Score
    for user in selected:
        user["score"] = score_user(user)

    # Step 7: Persist to Google Sheets
    total_saved, power_saved = save_results(selected)

    above = sum(1 for u in selected if u["score"] >= 65)
    logger.info(
        "Done. %d/%d users scored ≥65 (power users). %d written to sheet.",
        above,
        len(selected),
        power_saved,
    )


if __name__ == "__main__":
    run()
