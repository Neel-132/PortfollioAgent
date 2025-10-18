# backend/utils/prefetch_market_data.py

import logging
import os
import json
from datetime import datetime
from typing import List, Dict
from backend.utils.market_utils import fetch_news_data
from backend.utils.get_sec_fillings import fetch_sec_filings
import backend.constant as constant

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s')

CACHE_FILE = constant.CACHE_MARKETDATA_FILE


def _load_existing_cache() -> Dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load existing market cache: {e}")
    return {}


def _save_cache(cache: Dict):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def prefetch_market_data(tickers: List[str]):
    """
    Prefetch news and filings for all tickers.
    This should run at startup or on client login.
    """
    logger.info(f"Starting prefetch for {len(tickers)} tickers")

    cache = _load_existing_cache()
    updated_cache = {}

    for ticker in tickers:
        ticker = ticker.upper()
        logger.info(f"Fetching news and filings for {ticker}")

        # 📰 News
        try:
            news_data = fetch_news_data([ticker])
        except Exception as e:
            logger.error(f"Failed to fetch news for {ticker}: {e}")
            news_data = {}

        # 📑 SEC Filings (or mock)
        try:
            filings_data = fetch_sec_filings([ticker])
        except Exception as e:
            logger.error(f"Failed to fetch filings for {ticker}: {e}")
            filings_data = {}

        updated_cache[ticker] = {
            "timestamp": datetime.utcnow().isoformat(),
            "news": news_data.get(ticker, []),
            "filings": filings_data.get(ticker, [])
        }

    # Merge with existing cache
    cache.update(updated_cache)
    _save_cache(cache)

    logger.info(f"Prefetch completed for {len(updated_cache)} tickers.")
    return updated_cache

if __name__ == "__main__":
    import pandas as pd
    data = pd.read_excel("backend/data/portfolios.xlsx")
    tickers = set(data["symbol"].tolist())
    prefetch_market_data(tickers)