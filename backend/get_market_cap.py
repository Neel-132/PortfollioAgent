import yfinance as yf
import pandas as pd

def classify_bucket(market_cap):
    market_cap_cr = market_cap / 1e7  # convert from INR to Cr if needed
    if market_cap_cr > 20000:
        return "Large Cap"
    elif market_cap_cr >= 5000:
        return "Mid Cap"
    elif market_cap_cr > 0:
        return "Small Cap"
    else:
        return "Unknown"

def add_market_cap_bucket(df):
    buckets = []
    for symbol in df['symbol']:
        try:
            ticker = yf.Ticker(f"{symbol}")  # NSE
            data = ticker.info
            mcap = data.get("marketCap", 0)
            buckets.append(classify_bucket(mcap))
        except Exception:
            buckets.append("Unknown")
    df['market_cap_bucket'] = buckets
    return df

# Example usage
if __name__ == "__main__":

    df = pd.DataFrame({
        "symbol": ["RELIANCE", "TCS", "PAYTM"],
        "quantity": [10, 5, 20]
    })
    df = pd.read_excel("backend/data/portfolios.xlsx")
    df = add_market_cap_bucket(df)
    