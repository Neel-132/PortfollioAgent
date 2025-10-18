import yfinance as yf
import logging
# Configure logging format
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s')

import yfinance as yf
from datetime import datetime, timedelta

def get_price_on_date(symbol: str, days_back: int) -> float:
    ticker = yf.Ticker(symbol)
    end_date = datetime.today()
    
    # Special case: current price
    if days_back == 0:
        data = ticker.history(period="1d")
        if data.empty:
            return 0.0
        logger.info(f"Fetched latest price for {symbol} on {end_date}: {data['Close'].iloc[-1]}")
        return float(data["Close"].iloc[-1])

    # Otherwise: historical price
    start_date = end_date - timedelta(days=days_back + 2)
    data = ticker.history(start=start_date, end=end_date)
    logger.info(f"Fetched latest price for {symbol} on {end_date}: {data['Close'].iloc[0]}")

    if data.empty:
        return 0.0
    return float(data["Close"].iloc[0])

def fetch_latest_prices(tickers: list[str]) -> dict[str, float]:
    """
    Fetch latest prices for a list of tickers once.
    Returns a dict: {symbol: price}.
    """
    prices = {}
    for t in tickers:
        try:
            data = yf.Ticker(t).history(period="1d")
            if not data.empty:
                prices[t] = float(data["Close"].iloc[-1])
            else:
                logger.warning(f"No price data found for {t}")
                prices[t] = 0.0
        except Exception as e:
            logger.error(f"Failed to fetch price for {t}: {e}")
            prices[t] = 0.0
    return prices

