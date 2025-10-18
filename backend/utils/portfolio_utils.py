# backend/utils/portfolio_utils.py

import logging
import pandas as pd
from typing import Dict, List, Any
from ..tools.stock_price_fetcher import fetch_latest_prices
from ..tools.portfolio_functions import PortfolioFunctions

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def extract_tickers_from_fn_calls(fn_calls: List[Dict]) -> List[str]:
    """
    Extract all tickers mentioned in the LLM's function calls.
    """
    tickers = set()
    for call in fn_calls:
        args = call.get("arguments", {})
        if "entities" in args:
            tickers.update(args["entities"])
        if "ticker" in args:
            tickers.add(args["ticker"])
    return list(tickers)


def process_portfolio_query(execution_plan: Dict, session: Dict, client_id: str) -> Dict[str, Any]:
    """
    Core logic for handling portfolio queries.

    Steps:
    1️. Get client's portfolio from session.
    2️. Extract tickers from LLM execution plan.
    3️. Fetch latest prices once.
    4️. Pass everything to PortfolioFunctions.
    5️. Execute all required portfolio computations.
    """
    fn_calls = execution_plan.get("function_calls", [])
    portfolio_map = session.get("portfolio", {})
    results = {}
    portfolio_records = portfolio_map.get(client_id)
    if len(portfolio_records) == 0:
        logger.warning(f"⚠️ No portfolio data found for client_id={client_id}")
        return {
            "status": "error",
            "message": f"No portfolio found for client {client_id}"
        }

    portfolio_df = pd.DataFrame(portfolio_records)
    if portfolio_df is None or portfolio_df.empty:
        logger.warning(f"⚠️ No portfolio data found for client_id={client_id}")
        return {
            "status": "error",
            "message": f"No portfolio found for client {client_id}"
        }

    if not fn_calls:
        logger.info(f"ℹ️ No function calls found in execution plan for client_id={client_id}")
        # return {
        #     "status": "no_action",
        #     "message": "No function calls to process."
        # }

        tickers = portfolio_df["symbol"].unique().tolist()
        price_cache = fetch_latest_prices(tickers)
        portfolio_functions = PortfolioFunctions(portfolio_df, price_cache)

        returns = portfolio_functions.get_returns(tickers)
        results = returns


    else:    # 🧠 Step 1: Extract tickers once
        tickers = extract_tickers_from_fn_calls(fn_calls)
        logger.debug(f"Extracted tickers from fn_calls: {tickers}")

        # 🪙 Step 2: Fetch latest prices (only once)
        if len(tickers) == 0:
            logger.info(f"No tickers found from query. Getting the latest price of all the tickers for client {client_id}")
            tickers = portfolio_df["symbol"].unique().tolist()
        price_cache = fetch_latest_prices(tickers)
        logger.info(f"Fetched latest prices for {len(price_cache)} symbols")

        # 🧮 Step 3: Initialize PortfolioFunctions
        portfolio_functions = PortfolioFunctions(portfolio_df, price_cache)

        # 🧭 Step 4: Execute each function sequentially
        results = {}
        for call in fn_calls:
            fn_name = call.get("name")
            args = call.get("arguments", {})

            fn = getattr(portfolio_functions, fn_name, None)
            if not fn:
                logger.error(f"❌ Function {fn_name} not found in PortfolioFunctions.")
                results[fn_name] = {"error": f"Function '{fn_name}' not implemented."}
                continue

            try:
                logger.info(f"▶ Executing {fn_name} with args: {args}")
                result = fn(**args)
                results[fn_name] = result
            except Exception as e:
                logger.exception(f"💥 Error executing {fn_name}")
                results[fn_name] = {"error": str(e)}

    # ✅ Step 5: Prepare structured response
    response = {
        "status": "success",
        "client_id": client_id,
        "results": results,
        "num_functions": len(fn_calls),
        "message": f"Processed {len(fn_calls)} portfolio functions successfully."
    }

    logger.info(f"✅ Portfolio query completed for client_id={client_id}")
    logger.debug(f"Response: {response}")

    return response
