PORTFOLIO_FUNCTION_SCHEMA = [
    {
        "name": "get_returns",
        "description": "Get the returns for specific tickers or the entire portfolio.",
        "parameters": {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of stock tickers."
                }
            }
        }
    },
    {
        "name": "compare_performance",
        "description": "Compare performance between multiple tickers.",
        "parameters": {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tickers to compare."
                }
            },
            "required": ["entities"]
        }
    },
    {
        "name": "get_best_performers",
        "description": "Get top N best performers in the portfolio.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of top performers."}
            }
        }
    },
    {
        "name": "get_worst_performers",
        "description": "Get bottom N performers in the portfolio.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of bottom performers."}
            }
        }
    },
    {
        "name": "get_weight_in_portfolio",
        "description": "Get the portfolio weight of a specific ticker.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Ticker symbol."}
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "get_allocation",
        "description": "Get portfolio allocation by sector or asset class.",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["sector", "asset_class"],
                    "description": "Allocation grouping type."
                }
            }
        }
    },
    {
        "name": "get_holdings",
        "description": "Get all holdings in the user's portfolio.",
        "parameters": {
            "type": "object",
            "properties": {
                "include_details": {
                    "type": "boolean",
                    "description": "Whether to include detailed information such as quantity and purchase price.",
                    "default": False
                }
            }
        }
    },
    {
        "name": "get_market_cap_allocation",
        "description": "Get portfolio allocation by market cap bucket (e.g., Large Cap, Mid Cap, Small Cap, Unknown).",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
]
