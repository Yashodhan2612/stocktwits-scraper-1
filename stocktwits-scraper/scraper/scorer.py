"""
Power-user scoring: 1–100.

All dimensions are derived from fields actually returned by the StockTwits
public API (confirmed via live test). Per-message likes/replies are NOT
returned by the public endpoint, so scoring uses lifetime user stats instead.

Dimensions and max points:
  Ticker breadth (today's feed)  20 pts  – distinct tickers they posted in
  Lifetime posts (ideas)         25 pts  – total posts ever on StockTwits
  Follower count                 25 pts  – social reach / influence proxy
  Lifetime likes (like_count)    15 pts  – historical quality signal
  Watchlist diversity            10 pts  – proxy for research depth
  Verified bonus (official)       5 pts  – StockTwits official/verified

Target: ≥65 = StockDashboard power-user candidate.
Thresholds are generous so that active retail traders — not just mega-
influencers — can qualify.
"""


def score_user(user: dict) -> int:
    score = 0

    # --- Ticker breadth in today's feed (20 pts) ---
    tickers = len(user.get("tickers_seen", set()))
    if tickers >= 5:
        score += 20
    elif tickers >= 3:
        score += 16
    elif tickers >= 2:
        score += 11
    elif tickers >= 1:
        score += 7
    else:
        score += 2

    # --- Lifetime posts / ideas (25 pts) ---
    ideas = user.get("ideas", 0) or 0
    if ideas >= 1000:
        score += 25
    elif ideas >= 300:
        score += 19
    elif ideas >= 100:
        score += 13
    elif ideas >= 20:
        score += 8
    else:
        score += 3

    # --- Follower count (25 pts) ---
    followers = user.get("followers", 0) or 0
    if followers >= 500:
        score += 25
    elif followers >= 150:
        score += 19
    elif followers >= 50:
        score += 13
    elif followers >= 15:
        score += 8
    else:
        score += 3

    # --- Lifetime likes received (15 pts) ---
    like_count = user.get("like_count", 0) or 0
    if like_count >= 500:
        score += 15
    elif like_count >= 150:
        score += 11
    elif like_count >= 50:
        score += 7
    else:
        score += 3

    # --- Watchlist diversity (10 pts) ---
    watchlist = user.get("watchlist_stocks_count", 0) or 0
    if watchlist >= 25:
        score += 10
    elif watchlist >= 10:
        score += 8
    elif watchlist >= 5:
        score += 5
    else:
        score += 2

    # --- Verified bonus (5 pts) ---
    if user.get("verified"):
        score += 5

    return min(score, 100)
