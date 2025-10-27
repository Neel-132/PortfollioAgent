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

def extract_all_stock_entities(classification_result):
    """
    Extract all stock ticker entities from the new classification format
    and return them as a single flat list.
    """
    all_tickers = []
    
    # Extract from current query entities
    if "entities" in classification_result and "stocks" in classification_result["entities"]:
        for stock in classification_result["entities"]["stocks"]:
            if isinstance(stock, dict) and "ticker" in stock:
                ticker = stock["ticker"]
                # Skip unresolved entities
                if ticker != "UNRESOLVED":
                    all_tickers.append(ticker)
            elif isinstance(stock, str):
                # Handle case where stock is just a string ticker
                all_tickers.append(stock)
    
    # Extract from context entities
    if "context_entities" in classification_result and "stocks" in classification_result["context_entities"]:
        for stock in classification_result["context_entities"]["stocks"]:
            if isinstance(stock, dict) and "ticker" in stock:
                ticker = stock["ticker"]
                if ticker != "UNRESOLVED":
                    all_tickers.append(ticker)
            elif isinstance(stock, str):
                all_tickers.append(stock)
    
    # Deduplicate while preserving order
    seen = set()
    unique_tickers = []
    for ticker in all_tickers:
        if ticker not in seen:
            seen.add(ticker)
            unique_tickers.append(ticker)
    
    return unique_tickers

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

    # Get classification result
    result = agent.llm_classify(test_symbol_map, query, session.get("chat_history", []))
    
    # Extract all stock entities into a single flat list
    predicted_entities = extract_all_stock_entities(result)
    
    # Compare intent and entities
    intent_match = result["intent"] == case["expected_intent"]
    entity_match = set(predicted_entities) == set(case["expected_entities"])
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
        "predicted_entities": predicted_entities,
        "expected_entities": case["expected_entities"],
        "intent_match": intent_match,
        "entity_match": entity_match,
        "pass": passed,
        "full_classification": result  # Store full result for debugging
    })

# Accuracy metrics
total_cases = len(test_cases)
overall_accuracy = sum(r["pass"] for r in results) / total_cases * 100
intent_accuracy = intent_correct / total_cases * 100
entity_accuracy = entity_correct / total_cases * 100

# Detailed failure analysis
failed_cases = [r for r in results if not r["pass"]]
intent_failures = [r for r in results if not r["intent_match"]]
entity_failures = [r for r in results if not r["entity_match"]]

# Save results to file
output_file = f"evaluations/query_classification_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump({
        "results": results,
        "metrics": {
            "total_cases": total_cases,
            "passed_cases": sum(r["pass"] for r in results),
            "failed_cases": len(failed_cases),
            "overall_accuracy": overall_accuracy,
            "intent_accuracy": intent_accuracy,
            "entity_accuracy": entity_accuracy,
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

# Summary output
print("=" * 60)
print("QUERY CLASSIFICATION EVALUATION RESULTS")
print("=" * 60)
print(f"\n✅ Passed: {sum(r['pass'] for r in results)}/{total_cases} test cases")
print(f"\n📊 Overall Accuracy: {overall_accuracy:.2f}%")
print(f"🧠 Intent Accuracy: {intent_accuracy:.2f}%")
print(f"🏷️  Entity Accuracy: {entity_accuracy:.2f}%")

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

print(f"\n💾 Full results saved to {output_file}")
print("=" * 60)