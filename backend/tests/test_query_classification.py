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
    # --- Portfolio Intent ---
    {"query": "What are my holdings?", "expected_intent": "portfolio", "expected_entities": []},
    {"query": "Show me Apple’s performance", "expected_intent": "portfolio", "expected_entities": ["AAPL"]},
    {"query": "Compare Tesla and Microsoft", "expected_intent": "portfolio", "expected_entities": ["TSLA", "MSFT"]},
    {"query": "How is it performing?", "context": "Show me Tesla", "expected_intent": "portfolio", "expected_entities": ["TSLA"]},
    {"query": "Compare them", "context": "Show me Tesla and Microsoft", "expected_intent": "portfolio", "expected_entities": ["TSLA", "MSFT"]},
    {"query": "Add Amazon to my portfolio", "expected_intent": "portfolio", "expected_entities": ["AMZN"]},
    {"query": "Remove Tesla from my portfolio", "expected_intent": "portfolio", "expected_entities": ["TSLA"]},
    {"query": "Rebalance my portfolio", "expected_intent": "portfolio", "expected_entities": []},
    {"query": "Show me my gains in Apple and Amazon", "expected_intent": "portfolio", "expected_entities": ["AAPL", "AMZN"]},
    {"query": "Check Microsoft and Google in my portfolio", "expected_intent": "portfolio", "expected_entities": ["MSFT", "GOOG"]},

    # --- Market Intent ---
    {"query": "Latest news on Tesla", "expected_intent": "market", "expected_entities": ["TSLA"]},
    {"query": "Tell me about Google", "expected_intent": "market", "expected_entities": ["GOOG"]},
    {"query": "What's the market sentiment today?", "expected_intent": "market", "expected_entities": []},
    {"query": "What’s happening with Amazon lately?", "expected_intent": "market", "expected_entities": ["AMZN"]},
    {"query": "How is Apple performing in the market?", "expected_intent": "market", "expected_entities": ["AAPL"]},

    # --- Hybrid Intent ---
    {"query": "Does Apple's earnings affect my portfolio?", "expected_intent": "hybrid", "expected_entities": ["AAPL"]},
    {"query": "Will Tesla’s price drop impact my portfolio?", "expected_intent": "hybrid", "expected_entities": ["TSLA"]},
    {"query": "Will news about Microsoft and Google change my returns?", "expected_intent": "hybrid", "expected_entities": ["MSFT", "GOOG"]},

    # --- Unknown / Fallback ---
    {"query": "Blah blah blah", "expected_intent": "unknown", "expected_entities": []},
    {"query": "What do you think about life?", "expected_intent": "unknown", "expected_entities": []}
]

# Metrics counters
results = []
intent_correct = 0
entity_correct = 0

# Entity precision/recall components
total_tp_entities = 0
total_fp_entities = 0
total_fn_entities = 0

for case in test_cases:
    query = case["query"]
    context = case.get("context")

    session = {"chat_history": []}
    if context:
        session["chat_history"].append({
            "user": {"role": "user", "text": context},
            "system": {"role": "assistant", "text": ""}
        })

    # Run classification
    result = agent.llm_classify(test_symbol_map, query, session.get("chat_history", []))
    predicted_entities = result.get('entities', [])

    expected_entities = case["expected_entities"]
    predicted_intent = result["intent"]
    expected_intent = case["expected_intent"]

    # Intent match
    intent_match = predicted_intent == expected_intent
    if intent_match:
        intent_correct += 1

    # Entity match (for accuracy)
    entity_match = set(predicted_entities) == set(expected_entities)
    if entity_match:
        entity_correct += 1

    # Entity TP, FP, FN for precision/recall
    tp = len(set(predicted_entities) & set(expected_entities))
    fp = len(set(predicted_entities) - set(expected_entities))
    fn = len(set(expected_entities) - set(predicted_entities))

    total_tp_entities += tp
    total_fp_entities += fp
    total_fn_entities += fn

    results.append({
        "query": query,
        "context": context,
        "predicted_intent": predicted_intent,
        "expected_intent": expected_intent,
        "predicted_entities": predicted_entities,
        "expected_entities": expected_entities,
        "intent_match": intent_match,
        "entity_match": entity_match,
        "pass": intent_match and entity_match,
        "full_classification": result
    })

# Accuracy
total_cases = len(test_cases)
overall_accuracy = sum(r["pass"] for r in results) / total_cases * 100
intent_accuracy = intent_correct / total_cases * 100
entity_accuracy = entity_correct / total_cases * 100

# Precision, Recall, F1
# Intent: same as accuracy since single-label
intent_precision = intent_recall = intent_accuracy / 100
intent_f1 = (2 * intent_precision * intent_recall) / (intent_precision + intent_recall) if (intent_precision + intent_recall) else 0

# Entity
entity_precision = total_tp_entities / (total_tp_entities + total_fp_entities) if (total_tp_entities + total_fp_entities) > 0 else 0
entity_recall = total_tp_entities / (total_tp_entities + total_fn_entities) if (total_tp_entities + total_fn_entities) > 0 else 0
entity_f1 = (2 * entity_precision * entity_recall) / (entity_precision + entity_recall) if (entity_precision + entity_recall) > 0 else 0

# Failure analysis
failed_cases = [r for r in results if not r["pass"]]
intent_failures = [r for r in results if not r["intent_match"]]
entity_failures = [r for r in results if not r["entity_match"]]

# Save results
output_file = f"evaluations/query_classification_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump({
        "results": results,
        "metrics": {
            "total_cases": total_cases,
            "overall_accuracy": overall_accuracy,
            "intent_accuracy": intent_accuracy,
            "entity_accuracy": entity_accuracy,
            "intent_precision": intent_precision,
            "intent_recall": intent_recall,
            "intent_f1": intent_f1,
            "entity_precision": entity_precision,
            "entity_recall": entity_recall,
            "entity_f1": entity_f1,
            "intent_failures": len(intent_failures),
            "entity_failures": len(entity_failures)
        },
        "failure_analysis": {
            "intent_failures": [
                {
                    "query": r["query"],
                    "context": r["context"],
                    "predicted": r["predicted_intent"],
                    "expected": r["expected_intent"]
                }
                for r in intent_failures
            ],
            "entity_failures": [
                {
                    "query": r["query"],
                    "context": r["context"],
                    "predicted": r["predicted_entities"],
                    "expected": r["expected_entities"]
                }
                for r in entity_failures
            ]
        }
    }, f, indent=2)

# Summary
print("=" * 60)
print("QUERY CLASSIFICATION EVALUATION RESULTS")
print("=" * 60)
print(f"\n✅ Passed: {sum(r['pass'] for r in results)}/{total_cases} test cases")
print(f"\n📊 Overall Accuracy: {overall_accuracy:.2f}%")
print(f"🧠 Intent Accuracy: {intent_accuracy:.2f}%")
print(f"🏷️  Entity Accuracy: {entity_accuracy:.2f}%")

print("\n--- Precision / Recall / F1 ---")
print(f"Intent  →  Precision: {intent_precision:.2f} | Recall: {intent_recall:.2f} | F1: {intent_f1:.2f}")
print(f"Entity  →  Precision: {entity_precision:.2f} | Recall: {entity_recall:.2f} | F1: {entity_f1:.2f}")

if failed_cases:
    print(f"\n❌ Failed Cases: {len(failed_cases)}")
    print("\nFailure Details:")
    for i, failure in enumerate(failed_cases, 1):
        print(f"\n  {i}. Query: '{failure['query']}'")
        if failure['context']:
            print(f"     Context: '{failure['context']}'")
        if not failure['intent_match']:
            print(f"     ❌ Intent: {failure['predicted_intent']} (expected: {failure['expected_intent']})")
        if not failure['entity_match']:
            print(f"     ❌ Entities: {failure['predicted_entities']} (expected: {failure['expected_entities']})")

print(f"\nFull results saved to {output_file}")
print("=" * 60)
