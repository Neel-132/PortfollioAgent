import json
from datetime import datetime
from backend.agents.query_classifier import QueryClassificationAgent

# Initialize agent
agent = QueryClassificationAgent()

# Symbol map for normalization
test_symbol_map = {
    "TSLA": ["tesla", "tesla inc"],
    "MSFT": ["microsoft", "microsoft corporation"],
    "AAPL": ["apple", "apple inc"],
    "GOOG": ["google", "alphabet"],
    "AMZN": ["amazon", "amazon inc"]
}

# Test cases
test_cases = [
    {"query": "What are my holdings?", "expected_intent": "portfolio", "expected_entities": []},
    {"query": "Latest news on Tesla", "expected_intent": "market", "expected_entities": ["TSLA"]},
    {"query": "Compare Tesla and Microsoft", "expected_intent": "portfolio", "expected_entities": ["TSLA", "MSFT"]},
    {"query": "How is it performing?", "context": "Show me Tesla", "expected_intent": "portfolio", "expected_entities": ["TSLA"]},
    {"query": "Compare them", "context": "Show me Tesla and Microsoft", "expected_intent": "portfolio", "expected_entities": ["TSLA", "MSFT"]},
    {"query": "Does Apple's earnings affect my portfolio?", "expected_intent": "hybrid", "expected_entities": ["AAPL"]},
    {"query": "Show me Amazon's performance", "expected_intent": "portfolio", "expected_entities": ["AMZN"]},
    {"query": "What is the market sentiment today?", "expected_intent": "market", "expected_entities": []},
    {"query": "Tell me about Google", "expected_intent": "market", "expected_entities": ["GOOG"]},
    {"query": "Blah blah blah", "expected_intent": "unknown", "expected_entities": []}
]

# Evaluation loop
results = []
intent_correct = 0
entity_correct = 0
for case in test_cases:
    query = case["query"]
    context = case.get("context")

    session = {"chat_history": []}
    if context:
        session["chat_history"].append({
            "user": {"role": "user", "text": context},
            "system": {"role": "assistant", "text": ""}
        })

    result = agent.classify(query, session.get("chat_history", []), test_symbol_map)
    intent_match = result["intent"] == case["expected_intent"]
    entity_match = set(result["entities"]) == set(case["expected_entities"])
    passed = intent_match and entity_match

    if intent_match:
        intent_correct += 1
    if entity_match:
        entity_correct += 1

    results.append({
        "query": query,
        "context": context,
        "predicted_intent": result["intent"],
        "expected_intent": case["expected_intent"],
        "predicted_entities": result["entities"],
        "expected_entities": case["expected_entities"],
        "pass": passed
    })

# Accuracy metrics
total_cases = len(test_cases)
overall_accuracy = sum(r["pass"] for r in results) / total_cases * 100
intent_accuracy = intent_correct / total_cases * 100
entity_accuracy = entity_correct / total_cases * 100

# Save results to file
output_file = f"query_classification_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump({
        "results": results,
        "metrics": {
            "total_cases": total_cases,
            "overall_accuracy": overall_accuracy,
            "intent_accuracy": intent_accuracy,
            "entity_accuracy": entity_accuracy
        }
    }, f, indent=2)

# Summary
print(f"✅ Passed {sum(r['pass'] for r in results)}/{total_cases} test cases")
print(f"📊 Overall Accuracy: {overall_accuracy:.2f}%")
print(f"🧠 Intent Accuracy: {intent_accuracy:.2f}%")
print(f"🏷️ Entity Accuracy: {entity_accuracy:.2f}%")
print(f"Results saved to {output_file}")
