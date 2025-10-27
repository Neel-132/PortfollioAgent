import json
from datetime import datetime
from backend.utils.planner_utils import process_planning  # your planning function
from ..schemas.portfolio_function_schema import PORTFOLIO_FUNCTION_SCHEMA
from backend.utils.gemini_client import GeminiClient  # Mock if needed

# -----------------------------------------
# Test Routing Table (minimal mock)
# -----------------------------------------
routing_table = {
    "portfolio": ["PortfolioAgent"],
    "market": ["MarketAgent"],
    "hybrid": ["PortfolioAgent", "MarketAgent"]
}

# -----------------------------------------
# Updated Test Cases (aligned with latest prompt)
# -----------------------------------------
test_cases = [
    # 1. Single ticker returns
    {
        "query": "What is my return on Tesla?",
        "intent": "portfolio",
        "entities": {
            "tickers": ["TSLA"],
            "temporal": [],
            "financial_metrics": ["returns"],
            "events": []
        },
        "expected_function_calls": ["get_returns"]
    },
    # 2. Comparison between multiple tickers
    {
        "query": "Compare Tesla and Microsoft",
        "intent": "portfolio",
        "entities": {
            "tickers": ["TSLA", "MSFT"],
            "temporal": [],
            "financial_metrics": [],
            "events": []
        },
        "expected_function_calls": ["compare_performance"]
    },
    # 3. Allocation query without entities
    {
        "query": "Show my portfolio allocation by sector",
        "intent": "portfolio",
        "entities": {
            "tickers": [],
            "temporal": [],
            "financial_metrics": [],
            "events": []
        },
        "expected_function_calls": ["get_allocation"]
    },
    # 4. Best performers
    {
        "query": "What are my best performing stocks?",
        "intent": "portfolio",
        "entities": {
            "tickers": [],
            "temporal": [],
            "financial_metrics": [],
            "events": []
        },
        "expected_function_calls": ["get_best_performers"]
    },
    # 5. Holdings list
    {
        "query": "Which stocks do I own?",
        "intent": "portfolio",
        "entities": {
            "tickers": [],
            "temporal": [],
            "financial_metrics": [],
            "events": []
        },
        "expected_function_calls": ["get_holdings"]
    },
    # 6. Hybrid — news/earnings impact on portfolio
    {
        "query": "Does Apple's earnings affect my portfolio?",
        "intent": "hybrid",
        "entities": {
            "tickers": ["AAPL"],
            "temporal": [],
            "financial_metrics": ["performance"],
            "events": ["earnings"]
        },
        "expected_function_calls": ["get_returns"]
    },
    # 7. Performance of multiple tickers (context)
    {
        "query": "How are they performing?",
        "intent": "portfolio",
        "entities": {
            "tickers": ["TSLA", "MSFT"],
            "temporal": [],
            "financial_metrics": ["performance"],
            "events": []
        },
        "expected_function_calls": ["compare_performance"]
    },
    # 8. Temporal context - portfolio returns
    {
        "query": "Show me my Q3 returns",
        "intent": "portfolio",
        "entities": {
            "tickers": [],
            "temporal": ["Q3 2024"],
            "financial_metrics": ["returns"],
            "events": []
        },
        "expected_function_calls": ["get_returns"]
    },
    # 9. Single ticker returns (different ticker)
    {
        "query": "Show me Amazon's performance",
        "intent": "portfolio",
        "entities": {
            "tickers": ["AMZN"],
            "temporal": [],
            "financial_metrics": ["performance"],
            "events": []
        },
        "expected_function_calls": ["get_returns"]
    },
    # 10. Multiple tickers weight query (multi-function)
    {
        "query": "What's the weight of Tesla and Apple?",
        "intent": "portfolio",
        "entities": {
            "tickers": ["TSLA", "AAPL"],
            "temporal": [],
            "financial_metrics": [],
            "events": []
        },
        "expected_function_calls": ["get_weight_in_portfolio", "get_weight_in_portfolio"]
    }
]

# -----------------------------------------
# Evaluation Metrics
# -----------------------------------------
results = []
correct_count = 0
fallback_count = 0

for case in test_cases:
    session = {"chat_history": []}
    classification_result = {
        "intent": case["intent"],
        "entities": case["entities"],
        "confidence": 0.95
    }

    plan = process_planning(classification_result, routing_table, case["query"], session)

    # Extract function calls
    predicted_functions = [fc["name"] for fc in plan.get("function_calls", [])] if "function_calls" in plan else []

    expected = case["expected_function_calls"]
    predicted = predicted_functions

    # Exact match for order-sensitive multi-function calls
    is_correct = expected == predicted

    if is_correct:
        correct_count += 1

    if plan.get("requires_clarification") or "RuleBasedFallback" in plan.get("debug", {}):
        fallback_count += 1

    results.append({
        "query": case["query"],
        "intent": case["intent"],
        "entities": case["entities"],
        "expected_functions": expected,
        "predicted_functions": predicted,
        "pass": is_correct
    })

# -----------------------------------------
# Compute KPIs
# -----------------------------------------
total_cases = len(test_cases)
accuracy = (correct_count / total_cases) * 100
fallback_rate = (fallback_count / total_cases) * 100

metrics = {
    "total_cases": total_cases,
    "function_call_accuracy": accuracy,
    "fallback_usage_rate": fallback_rate
}

# -----------------------------------------
# Save Results
# -----------------------------------------
output_file = f"function_calling_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump({"results": results, "metrics": metrics}, f, indent=2)

print(f"✅ Function Calling Evaluation Complete")
print(f"📊 Function Call Accuracy: {accuracy:.2f}%")
print(f"🛠️ Fallback Usage Rate: {fallback_rate:.2f}%")
print(f"📝 Results saved to: {output_file}")
