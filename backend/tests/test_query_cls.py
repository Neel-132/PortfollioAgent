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
true_positive_entities = 0
total_expected_entities = 0
total_predicted_entities = 0
context_cases = 0
context_correct = 0
unknown_total = 0
unknown_correct = 0

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

    expected_entities = set(case["expected_entities"])
    predicted_entities = set(result["entities"])

    intent_match = result["intent"] == case["expected_intent"]
    entity_match = (expected_entities == predicted_entities) or (len(predicted_entities.intersection(expected_entities)) > 0
)
    # Entity precision & recall counts
    true_positive_entities += len(predicted_entities & expected_entities)
    total_expected_entities += len(expected_entities)
    total_predicted_entities += len(predicted_entities)

    # Context resolution metric
    if context:
        context_cases += 1
        if entity_match and intent_match:
            context_correct += 1

    # Unknown detection metric
    if case["expected_intent"] == "unknown":
        unknown_total += 1
        if intent_match:
            unknown_correct += 1

    if intent_match:
        intent_correct += 1
    if entity_match:
        entity_correct += 1

    results.append({
        "query": query,
        "context": context,
        "predicted_intent": result["intent"],
        "expected_intent": case["expected_intent"],
        "predicted_entities": list(predicted_entities),
        "expected_entities": list(expected_entities),
        "pass": intent_match and entity_match
    })

# Accuracy metrics
total_cases = len(test_cases)
overall_accuracy = sum(r["pass"] for r in results) / total_cases * 100
intent_accuracy = intent_correct / total_cases * 100
entity_accuracy = entity_correct / total_cases * 100

# Entity precision and recall
entity_precision = (true_positive_entities / total_predicted_entities * 100) if total_predicted_entities else 0
entity_recall = (true_positive_entities / total_expected_entities * 100) if total_expected_entities else 0

# Context resolution accuracy
context_resolution_accuracy = (context_correct / context_cases * 100) if context_cases else 0

# Unknown detection accuracy
unknown_detection_accuracy = (unknown_correct / unknown_total * 100) if unknown_total else 0

# Save results to file
output_file = f"query_classification_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump({
        "results": results,
        "metrics": {
            "total_cases": total_cases,
            "overall_accuracy": overall_accuracy,
            "intent_accuracy": intent_accuracy,
            "entity_accuracy": entity_accuracy,
            "entity_precision": entity_precision,
            "entity_recall": entity_recall,
            "context_resolution_accuracy": context_resolution_accuracy,
            "unknown_detection_accuracy": unknown_detection_accuracy
        }
    }, f, indent=2)

# Summary
print(f"✅ Passed {sum(r['pass'] for r in results)}/{total_cases} test cases")
print(f"📊 Overall Accuracy: {overall_accuracy:.2f}%")
print(f"🧠 Intent Accuracy: {intent_accuracy:.2f}%")
print(f"🏷️ Entity Accuracy: {entity_accuracy:.2f}%")
print(f"🎯 Entity Precision: {entity_precision:.2f}% | Recall: {entity_recall:.2f}%")
print(f"🧭 Context Resolution Accuracy: {context_resolution_accuracy:.2f}%")
print(f"❓ Unknown Detection Accuracy: {unknown_detection_accuracy:.2f}%")
print(f"Results saved to {output_file}")
