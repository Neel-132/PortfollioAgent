import json
from datetime import datetime
from backend.utils.validation_utils import run_validation

# Define test cases
import json
from datetime import datetime
from backend.utils.validation_utils import run_validation

test_cases = [
    # 1. ✅ Normal portfolio flow
    {
        "query": "What are my holdings?",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "portfolio", "entities": []}},
                {"agent": "PlannerAgent", "output": {"function_calls": [{"name": "get_holdings"}]}},
                {"agent": "PortfolioAgent", "output": {"status": "success", "results": [{"symbol": "TSLA"}]}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": "You currently hold TSLA."}}
            ]
        },
        "expected_result": "pass"
    },

    # 2. ❌ PlannerAgent fails
    {
        "query": "Compare Tesla and Microsoft",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "portfolio", "entities": ["TSLA", "MSFT"]}},
                {"agent": "PlannerAgent", "output": {"function_calls": []}},
                {"agent": "PortfolioAgent", "output": {"status": "success"}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": ""}}
            ]
        },
        "expected_result": "fail",
        "expected_failed_agent": "QueryClassificationAgent"
    },

    # 3. ❌ PortfolioAgent fails
    {
        "query": "Show me Amazon's performance",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "portfolio", "entities": ["AMZN"]}},
                {"agent": "PlannerAgent", "output": {"function_calls": [{"name": "get_returns"}]}},
                {"agent": "PortfolioAgent", "output": {"status": "failed", "results": []}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": ""}}
            ]
        },
        "expected_result": "fail",
        "expected_failed_agent": "PortfolioAgent"
    },

    # 4. ✅ Market flow works
    {
        "query": "What's the market sentiment today?",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "market", "entities": []}},
                {"agent": "PlannerAgent", "output": {"function_calls": []}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": "Market sentiment is positive."}}
            ]
        },
        "expected_result": "pass"
    },

    # 5. ✅ Portfolio with multiple entities
    {
        "query": "How are they performing?",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "portfolio", "entities": ["TSLA", "MSFT"]}},
                {"agent": "PlannerAgent", "output": {"function_calls": [{"name": "compare_performance"}]}},
                {"agent": "PortfolioAgent", "output": {"status": "success"}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": "TSLA is up 20%, MSFT is up 15%."}}
            ]
        },
        "expected_result": "pass"
    },

    # 6. ❌ Classification fails
    {
        "query": "How is Tesla performing?",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "unknown", "entities": ["TSLA"]}},
                {"agent": "PlannerAgent", "output": {"function_calls": []}},
                {"agent": "PortfolioAgent", "output": {"status": "success"}}
            ]
        },
        "expected_result": "fail",
        "expected_failed_agent": "QueryClassificationAgent"
    },

    # 7. ❌ Response Generator fails
    {
        "query": "Show my portfolio allocation by sector",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "portfolio", "entities": []}},
                {"agent": "PlannerAgent", "output": {"function_calls": [{"name": "get_allocation"}]}},
                {"agent": "PortfolioAgent", "output": {"status": "success", "results": [{"sector": "Tech"}]}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": ""}}
            ]
        },
        "expected_result": "fail",
        "expected_failed_agent": "ResponseGeneratorAgent"
    },

    # 8. ✅ Hybrid intent passes
    {
        "query": "Does Apple's earnings affect my portfolio?",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "hybrid", "entities": ["AAPL"]}},
                {"agent": "PlannerAgent", "output": {"function_calls": [{"name": "get_returns"}]}},
                {"agent": "PortfolioAgent", "output": {"status": "success"}},
                {"agent": "MarketAgent", "output": {"status": "success", "news": ["Apple announces strong Q4 earnings"]}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": "Apple (AAPL) is up 3% after Q4 earnings."}}
            ]
        },
        "expected_result": "pass"
    },

    # 9. ❌ MarketAgent fails (empty output)
    {
        "query": "What happened to Apple in the news?",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "market", "entities": ["AAPL"]}},
                {"agent": "PlannerAgent", "output": {"function_calls": []}},
                {"agent": "MarketAgent", "output": {"status": "failed", "news": []}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": ""}}
            ]
        },
        "expected_result": "fail",
        "expected_failed_agent": "MarketAgent"
    },

    # 10. ❌ Planner selects wrong agent
    {
        "query": "Tell me my portfolio value",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "portfolio", "entities": []}},
                {"agent": "PlannerAgent", "output": {"function_calls": [{"name": "get_holdings"}]}},  # Wrong function
                {"agent": "PortfolioAgent", "output": {"status": "success"}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": "Your holdings are TSLA and MSFT."}}
            ]
        },
        "expected_result": "fail",
        "expected_failed_agent": "PlannerAgent"
    }
]

test_cases = [
    # 1. ✅ Normal portfolio flow
    {
        "query": "What are my holdings?",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "portfolio", "entities": []}},
                {"agent": "PlannerAgent", "output": {"function_calls": [{"name": "get_holdings"}]}},
                {"agent": "PortfolioAgent", "output": {"status": "success", "results": [{"symbol": "TSLA"}]}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": "You currently hold TSLA."}}
            ]
        },
        "expected_result": "pass"
    },

    # 2. ❌ PlannerAgent fails (no function calls)
    {
        "query": "Compare Tesla and Microsoft",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "portfolio", "entities": ["TSLA", "MSFT"]}},
                {"agent": "PlannerAgent", "output": {"function_calls": []}},
                {"agent": "PortfolioAgent", "output": {"status": "success"}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": ""}}
            ]
        },
        "expected_result": "fail",
        "expected_failed_agent": "PlannerAgent"
    },

    # 3. ❌ PortfolioAgent fails
    {
        "query": "Show me Amazon's performance",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "portfolio", "entities": ["AMZN"]}},
                {"agent": "PlannerAgent", "output": {"function_calls": [{"name": "get_returns"}]}},
                {"agent": "PortfolioAgent", "output": {"status": "failed", "results": []}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": ""}}
            ]
        },
        "expected_result": "fail",
        "expected_failed_agent": "PortfolioAgent"
    },

    # 4. ✅ Market flow works
    {
        "query": "What's the market sentiment today?",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "market", "entities": []}},
                {"agent": "PlannerAgent", "output": {"function_calls": []}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": "Market sentiment is positive."}}
            ]
        },
        "expected_result": "pass"
    },

    # 5. ✅ Portfolio with multiple entities
    {
        "query": "How are they performing?",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "portfolio", "entities": ["TSLA", "MSFT"]}},
                {"agent": "PlannerAgent", "output": {"function_calls": [{"name": "compare_performance"}]}},
                {"agent": "PortfolioAgent", "output": {"status": "success"}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": "TSLA is up 20%, MSFT is up 15%."}}
            ]
        },
        "expected_result": "pass"
    },

    # 6. ❌ Classification fails
    {
        "query": "How is Tesla performing?",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "unknown", "entities": ["TSLA"]}},
                {"agent": "PlannerAgent", "output": {"function_calls": []}},
                {"agent": "PortfolioAgent", "output": {"status": "success"}}
            ]
        },
        "expected_result": "fail",
        "expected_failed_agent": "QueryClassificationAgent"
    },

    # 7. ❌ Response Generator fails
    {
        "query": "Show my portfolio allocation by sector",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "portfolio", "entities": []}},
                {"agent": "PlannerAgent", "output": {"function_calls": [{"name": "get_allocation"}]}},
                {"agent": "PortfolioAgent", "output": {"status": "success", "results": [{"sector": "Tech"}]}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": ""}}
            ]
        },
        "expected_result": "fail",
        "expected_failed_agent": "ResponseGeneratorAgent"
    },

    # 8. ✅ Hybrid intent passes
    {
        "query": "Does Apple's earnings affect my portfolio?",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "hybrid", "entities": ["AAPL"]}},
                {"agent": "PlannerAgent", "output": {"function_calls": [{"name": "get_returns"}]}},
                {"agent": "PortfolioAgent", "output": {"status": "success"}},
                {"agent": "MarketAgent", "output": {"status": "success", "news": ["Apple announces strong Q4 earnings"]}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": "Apple (AAPL) is up 3% after Q4 earnings."}}
            ]
        },
        "expected_result": "pass"
    },

    # 9. ❌ MarketAgent fails (empty output)
    {
        "query": "What happened to Apple in the news?",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "market", "entities": ["AAPL"]}},
                {"agent": "PlannerAgent", "output": {"function_calls": []}},
                {"agent": "MarketAgent", "output": {"status": "failed", "news": []}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": ""}}
            ]
        },
        "expected_result": "fail",
        "expected_failed_agent": "MarketAgent"
    },

    # 10. ❌ Planner selects wrong function
    {
        "query": "Tell me my portfolio value",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "portfolio", "entities": []}},
                {"agent": "PlannerAgent", "output": {"function_calls": [{"name": "get_holdings"}]}},  # Wrong function
                {"agent": "PortfolioAgent", "output": {"status": "success"}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": "Your holdings are TSLA and MSFT."}}
            ]
        },
        "expected_result": "fail",
        "expected_failed_agent": "PlannerAgent"
    },

    # 11. ❌ Missing entities for portfolio intent
    {
        "query": "How is it performing?",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "portfolio", "entities": []}},
                {"agent": "PlannerAgent", "output": {"function_calls": [{"name": "get_returns"}]}},
                {"agent": "PortfolioAgent", "output": {"status": "success"}}
            ]
        },
        "expected_result": "fail",
        "expected_failed_agent": "QueryClassificationAgent"
    },

    # 12. ❌ Hybrid intent but missing market data
    {
        "query": "What’s happening with Apple and my portfolio?",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "hybrid", "entities": ["AAPL"]}},
                {"agent": "PlannerAgent", "output": {"function_calls": [{"name": "get_returns"}]}},
                {"agent": "PortfolioAgent", "output": {"status": "success"}},
                {"agent": "MarketAgent", "output": {"status": "failed", "news": []}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": ""}}
            ]
        },
        "expected_result": "fail",
        "expected_failed_agent": "MarketAgent"
    },

    # 13. ❌ ResponseGenerator returns partial response
    {
        "query": "How is Tesla performing?",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "portfolio", "entities": ["TSLA"]}},
                {"agent": "PlannerAgent", "output": {"function_calls": [{"name": "get_returns"}]}},
                {"agent": "PortfolioAgent", "output": {"status": "success", "results": [{"symbol": "TSLA"}]}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": None}}
            ]
        },
        "expected_result": "fail",
        "expected_failed_agent": "ResponseGeneratorAgent"
    },

    # 14. ✅ Market + empty entities handled gracefully
    {
        "query": "Show me market overview",
        "workflow_steps": {
            "steps": [
                {"agent": "QueryClassificationAgent", "output": {"intent": "market", "entities": []}},
                {"agent": "PlannerAgent", "output": {"function_calls": []}},
                {"agent": "MarketAgent", "output": {"status": "success", "news": ["Markets are rallying today"]}},
                {"agent": "ResponseGeneratorAgent", "output": {"text": "Markets are rallying today."}}
            ]
        },
        "expected_result": "pass"
    }
]

# Evaluation
results = []
pass_count = 0
for case in test_cases:
    result = run_validation(case["query"], case["workflow_steps"])
    passed = (
        result["validation_result"] == case["expected_result"]
        and (
            case["expected_result"] == "pass" or
            result.get("failed_agent") == case.get("expected_failed_agent")
        )
    )

    if passed:
        pass_count += 1

    results.append({
        "query": case["query"],
        "expected_result": case["expected_result"],
        "actual_result": result["validation_result"],
        "expected_failed_agent": case.get("expected_failed_agent"),
        "actual_failed_agent": result.get("failed_agent"),
        "reason": result.get("reason"),
        "pass": passed
    })

# Metrics
total_cases = len(test_cases)
accuracy = pass_count / total_cases * 100

output_file = f"validator_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump({
        "results": results,
        "metrics": {
            "total_cases": total_cases,
            "accuracy": accuracy
        }
    }, f, indent=2)

# Summary
print(f"✅ Passed {pass_count}/{total_cases} test cases")
print(f"📊 Validator Accuracy: {accuracy:.2f}%")
print(f"Results saved to {output_file}")

# Evaluation
results = []
pass_count = 0
for case in test_cases:
    result = run_validation(case["query"], case["workflow_steps"])
    passed = (
        result["validation_result"] == case["expected_result"]
        or (result["failed_agent"] == case.get("expected_failed_agent"))
    )

    if passed:
        pass_count += 1

    results.append({
        "query": case["query"],
        "expected_result": case["expected_result"],
        "actual_result": result["validation_result"],
        "expected_failed_agent": case.get("expected_failed_agent"),
        "actual_failed_agent": result.get("failed_agent"),
        "reason": result.get("reason"),
        "pass": passed
    })

# Metrics
total_cases = len(test_cases)
accuracy = pass_count / total_cases * 100

output_file = f"validator_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump({
        "results": results,
        "metrics": {
            "total_cases": total_cases,
            "accuracy": accuracy
        }
    }, f, indent=2)

# Summary
print(f"✅ Passed {pass_count}/{total_cases} test cases")
print(f"📊 Validator Accuracy: {accuracy:.2f}%")
print(f"Results saved to {output_file}")
