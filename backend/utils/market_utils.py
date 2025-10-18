
import logging
import requests
import os
from datetime import datetime
from typing import List, Dict
import backend.constant as constant
from typing import List, Dict
import yfinance as yf
import json
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
FINNHUB_NEWS_ENDPOINT = constant.finhub_news_endpoint

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

CACHE_FILE = constant.CACHE_MARKETDATA_FILE

def fetch_news_data(entities: List[str], max_articles: int = 20) -> Dict[str, list]:
    """
    Fetch recent company-specific news for each ticker from Finnhub.
    If API key not available, return mock data.
    Returns {symbol: [ {title, source, published}, ... ]}
    """
    results = {}

    # Use the last 7 days as a window
    today = datetime.utcnow().date()
    from_date = today.replace(day=max(today.day - 7, 1))

    for symbol in entities:
        try:
            symbol = symbol.upper()

            if not FINNHUB_API_KEY:
                # Return mock if no key
                results[symbol] = [
                    {
                        "title": f"Mock financial news headline for {symbol}",
                        "source": "MockSource",
                        "published": datetime.utcnow().isoformat()
                    }
                ]
                continue

            params = {
                "symbol": symbol,
                "from": from_date.isoformat(),
                "to": today.isoformat(),
                "token": FINNHUB_API_KEY
            }

            resp = requests.get(FINNHUB_NEWS_ENDPOINT, params=params)
            resp.raise_for_status()
            news_items = resp.json()
          
            articles = []
            for item in news_items[:max_articles]:
                articles.append({
                    "title": item.get("headline", ""),
                    "source": item.get("source", ""),
                    "published": item.get("datetime", 0),
                    "summary": item.get("summary", "")
                })
            results[symbol] = articles

        except Exception as e:
            logger.error(f"Failed to fetch Finnhub news for {symbol}: {e}", exc_info=True)
            results[symbol] = []

    return results


def fetch_sec_filings(entities: List[str], max_filings: int = 2) -> Dict[str, list]:
    """
    Fetch or mock SEC filings for each ticker.
    For demo purposes, returns mock data.
    Returns {symbol: [ {type, title, date}, ... ] }
    """
    results = {}
    for symbol in entities:
        try:
            symbol = symbol.upper()

            # Mock filings
            results[symbol] = [
                {
                    "type": "8-K",
                    "title": f"Mock 8-K filing for {symbol}",
                    "date": datetime.utcnow().strftime("%Y-%m-%d")
                },
                {
                    "type": "10-Q",
                    "title": f"Mock quarterly filing for {symbol}",
                    "date": (datetime.utcnow().replace(day=1)).strftime("%Y-%m-%d")
                }
            ][:max_filings]

        except Exception as e:
            logger.error(f"Failed to fetch SEC filings for {symbol}: {e}", exc_info=True)
            results[symbol] = []

    return results
 




def _load_market_cache() -> Dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load market cache: {e}")
        return {}


def _save_market_cache(cache: Dict):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def get_latest_price(symbol: str) -> float:
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        if hist.empty:
            logger.warning(f"No price data found for {symbol}")
            return 0.0
        return float(hist["Close"].iloc[-1])
    except Exception as e:
        logger.error(f"Failed to fetch price for {symbol}: {e}", exc_info=True)
        return 0.0


def process_market_query(entities: List[str], session: Dict) -> Dict:
    """
    Core logic for handling market queries:
    - Reads cache for news/filings
    - Fetches from live APIs if not cached
    - Updates cache if needed
    - Always fetches latest price
    """
    cache = _load_market_cache()
    results = {}
    cache_updated = False

    for symbol in entities:
        symbol = symbol.upper()
        try:
            cached = cache.get(symbol, {})
            news_data = cached.get("news", [])
            filings_data = cached.get("filings", [])

            # If missing in cache, fetch fresh and update
            if not news_data:
                logger.info(f"No cached news for {symbol}. Fetching live...")
                fresh_news = fetch_news_data([symbol])
                news_data = fresh_news.get(symbol, [])
                cached["news"] = news_data
                cache_updated = True

            if not filings_data:
                logger.info(f"No cached filings for {symbol}. Fetching live...")
                fresh_filings = fetch_sec_filings([symbol])
                filings_data = fresh_filings.get(symbol, [])
                cached["filings"] = filings_data
                cache_updated = True

            # Always fetch latest price
            latest_price = get_latest_price(symbol)

            results[symbol] = {
                "latest_price": latest_price,
                "news": news_data,
                "filings": filings_data,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Save updated entry to cache
            cache[symbol] = cached

        except Exception as e:
            logger.error(f"Failed to process market data for {symbol}: {e}", exc_info=True)
            results[symbol] = {
                "latest_price": None,
                "news": [],
                "filings": [],
                "error": str(e)
            }

    if cache_updated:
        _save_market_cache(cache)

    return results



if __name__ == "__main__":
    print(fetch_news_data(["AAPL", "MSFT"]))