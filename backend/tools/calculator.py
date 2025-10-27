# backend/agents/calculator.py
from typing import List, Dict, Optional

class CalculatorTool:
    """
    Core math layer — uses precomputed price_cache (no API calls here).
    """

    def __init__(self, portfolio_df, price_cache: Dict[str, float]):
        self.portfolio_df = portfolio_df
        self.price_cache = price_cache

    
    # ---------- helpers ----------
    def _filter_holdings(self, tickers: Optional[List[str]] = None) -> List[Dict]:
        df = self.portfolio_df
        if tickers:
            df = df[df["symbol"].isin([t.upper() for t in tickers])]
        return df.to_dict(orient="records")

    def _get_price(self, symbol: str) -> float:
        return float(self.price_cache.get(symbol.upper(), 0.0))

    def _attach_prices(self, holdings: List[Dict]) -> List[Dict]:
        for item in holdings:
            item["current_price"] = self._get_price(item["symbol"])
        return holdings

    # ---------- core computations ----------
    def get_holdings(self, include_details: bool = False):
        """
        Returns portfolio holdings.
        If include_details=False → returns only list of tickers.
        If include_details=True  → returns full portfolio rows.
        """
        if include_details:
            return self.portfolio_df.to_dict(orient="records")
        else:
            return self.portfolio_df["symbol"].unique().tolist()
        
    def get_returns(self, tickers: Optional[List[str]] = None) -> Dict:
        holdings = self._attach_prices(self._filter_holdings(tickers))
        results = []
        for h in holdings:
            cost = h["Purchase Price"] * h["quantity"]
            gain = (h["current_price"] - h["Purchase Price"]) * h["quantity"]
            pct = (gain / cost * 100) if cost else 0.0
            results.append({
                "symbol": h["symbol"],
                "security_name": h["security_name"],
                "purchase_price": round(h["Purchase Price"], 2),
                "current_price": round(h["current_price"], 2),
                "quantity": h["quantity"],
                "gain": round(gain, 2),
                "pct_return": round(pct, 2)
            })
        return {"returns": results}

    def compare_performance(self, tickers: List[str]) -> Dict:
        holdings = self._attach_prices(self._filter_holdings(tickers))
        comparison: Dict[str, Dict] = {}
        for h in holdings:
            cost = h["Purchase Price"] * h["quantity"]
            gain = (h["current_price"] - h["Purchase Price"]) * h["quantity"]
            pct = (gain / cost * 100) if cost else 0.0
            comparison[h["symbol"].upper()] = {
                "current_price": round(h["current_price"], 2),
                "purchase_price": round(h["Purchase Price"], 2),
                "quantity": h["quantity"],
                "gain": round(gain, 2),
                "pct_return": round(pct, 2)
            }
        return {"comparison": comparison}

    def get_best_performers(self, limit: int = 3) -> Dict:
        """
        Return top N performers sorted by pct_return (descending).
        """
        holdings = self._attach_prices(self._filter_holdings())
        enriched = []
        for h in holdings:
            cost = h["Purchase Price"] * h["quantity"]
            gain = (h["current_price"] - h["Purchase Price"]) * h["quantity"]
            pct = (gain / cost * 100) if cost else 0.0
            enriched.append({**h, "gain": round(gain, 2), "pct_return": round(pct, 2)})
        top = sorted(enriched, key=lambda x: x["pct_return"], reverse=True)[: max(0, int(limit))]
        return {"best_performers": top}

    def get_worst_performers(self, limit: int = 3) -> Dict:
        """
        Return bottom N performers sorted by pct_return (ascending).
        """
        holdings = self._attach_prices(self._filter_holdings())
        enriched = []
        for h in holdings:
            cost = h["Purchase Price"] * h["quantity"]
            gain = (h["current_price"] - h["Purchase Price"]) * h["quantity"]
            pct = (gain / cost * 100) if cost else 0.0
            enriched.append({**h, "gain": round(gain, 2), "pct_return": round(pct, 2)})
        bottom = sorted(enriched, key=lambda x: x["pct_return"])[: max(0, int(limit))]
        return {"worst_performers": bottom}

    # (optional) allocation helpers you already had can remain as-is
    def get_allocation(self, type: str = "sector") -> Dict:
        holdings = self._attach_prices(self._filter_holdings())
        total_value = sum(h["quantity"] * h["current_price"] for h in holdings)
        allocs: Dict[str, float] = {}
        for h in holdings:
            key = h.get(type, "Unknown")
            allocs[key] = allocs.get(key, 0.0) + (h["quantity"] * h["current_price"])
        if total_value > 0:
            allocs = {k: round(v / total_value * 100, 2) for k, v in allocs.items()}
        else:
            allocs = {k: 0.0 for k in allocs}
        return {f"{type}_allocations": allocs}
    
    def get_weight_in_portfolio(self, ticker: str) -> Dict:
        holdings = self._attach_prices(self._filter_holdings())
        total_value = sum(item["quantity"] * item["current_price"] for item in holdings)
        ticker_holding = self._filter_holdings([ticker])

        if not ticker_holding or total_value == 0:
            return {"ticker": ticker, "weight_in_portfolio": 0.0}

        ticker_value = ticker_holding[0]["quantity"] * self._get_price(ticker)
        weight = (ticker_value / total_value) * 100

        return {"ticker": ticker, "weight_in_portfolio": round(weight, 2)}
    
    
    # def get_market_cap_allocation(self) -> Dict:
    #     """
    #     Calculate portfolio allocation by market cap bucket.
    #     Uses the `market_cap_bucket` column in the portfolio_df.
    #     """
    #     holdings = self._attach_prices(self._filter_holdings())
    #     total_value = sum(h["quantity"] * h["current_price"] for h in holdings)

    #     bucket_allocs: Dict[str, float] = {}
    #     for h in holdings:
    #         bucket = h.get("market_cap_bucket", "Unknown")
    #         value = h["quantity"] * h["current_price"]
    #         bucket_allocs[bucket] = bucket_allocs.get(bucket, 0.0) + value

    #     if total_value > 0:
    #         bucket_allocs = {
    #             k: round(v / total_value * 100, 2) for k, v in bucket_allocs.items()
    #         }
    #     else:
    #         bucket_allocs = {k: 0.0 for k in bucket_allocs}

    #     return {"market_cap_allocations": bucket_allocs}
    
    def get_market_cap_allocation(self) -> Dict:
        """
        Calculate portfolio allocation by market cap bucket.
        Uses the `market_cap_bucket` column in the portfolio_df.
        Returns allocation % and list of tickers under each bucket.
        """
        holdings = self._attach_prices(self._filter_holdings())
        total_value = sum(h["quantity"] * h["current_price"] for h in holdings)

        bucket_allocs: Dict[str, Dict] = {}
        for h in holdings:
            bucket = h.get("market_cap_bucket", "Unknown")
            value = h["quantity"] * h["current_price"]
            symbol = h["symbol"]

            if bucket not in bucket_allocs:
                bucket_allocs[bucket] = {"allocation_percent": 0.0, "symbols": [], "total_value": 0.0}

            bucket_allocs[bucket]["symbols"].append(symbol)
            bucket_allocs[bucket]["total_value"] += value

        # Calculate final allocation %
        for bucket, data in bucket_allocs.items():
            if total_value > 0:
                data["allocation_percent"] = round(data["total_value"] / total_value * 100, 2)
            else:
                data["allocation_percent"] = 0.0
            # Drop total_value from final response if not needed
            del data["total_value"]

        return {"market_cap_allocations": bucket_allocs}


