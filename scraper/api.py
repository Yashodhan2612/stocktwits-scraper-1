import logging
import time

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://api.stocktwits.com/api/2"

# 1.5s between requests keeps us well under the 200 req/hr public rate limit
REQUEST_DELAY = 1.5
# Back-off duration when a 429 is received
RATE_LIMIT_SLEEP = 65


def _get(path: str, params: dict | None = None) -> dict | None:
    url = f"{BASE_URL}/{path}"
    try:
        resp = requests.get(url, params=params, timeout=10, headers={"User-Agent": "stocktwits-scraper/1.0"})
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429:
            logger.warning("Rate limited — sleeping %ds", RATE_LIMIT_SLEEP)
            time.sleep(RATE_LIMIT_SLEEP)
            # One retry after back-off
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        logger.warning("HTTP %s for %s", resp.status_code, url)
    except requests.RequestException as exc:
        logger.error("Request error for %s: %s", url, exc)
    return None


def fetch_symbol_stream(symbol: str) -> list[dict]:
    """Return up to 30 recent messages for a stock symbol."""
    time.sleep(REQUEST_DELAY)
    data = _get(f"streams/symbol/{symbol}.json")
    if data and data.get("response", {}).get("status") == 200:
        return data.get("messages", [])
    return []
