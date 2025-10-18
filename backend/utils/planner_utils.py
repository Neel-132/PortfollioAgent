import logging
from typing import Dict, Any
from ..utils.gemini_client import GeminiClient
from ..schemas.portfolio_function_schema import PORTFOLIO_FUNCTION_SCHEMA
import backend.constant as constant
import re
import backend.constant as constant
import backend.utils.helper as helper




logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def generate_execution_plan(classification_result: Dict, routing_table: Dict) -> Dict:
    """
    Generates a basic execution plan from classification result
    and routing table (existing logic).
    """
    intent = classification_result.get("intent", "unknown")
    agents = routing_table.get(intent, [])
    return {
        "intent": intent,
        "entities": classification_result.get("entities", []),
        "confidence": classification_result.get("confidence", 0),
        "agents": agents
    }


def process_planning(classification_result: Dict, routing_table: Dict, user_query: str, session: Dict) -> Dict:
    """
    Core planning logic:
    - Get base execution plan from routing map
    - If portfolio intent -> call Gemini for function calling
    - If hybrid intent -> portfolio + future market handling
    """
    logger.info(f"Starting planning for: {classification_result}")

    intent = classification_result.get("intent", "unknown")
    entities = classification_result.get("entities", [])

    # Step 1: Generate base execution plan
    execution_plan = generate_execution_plan(classification_result, routing_table)
    execution_plan["intent"] = intent
    execution_plan["entities"] = entities
    chat_history = session.get("chat_history", [])
    # if len(chat_history) > 0:
    #     chat_history_string = "\n".join([
    #                 f"User: {turn['user']['text']}\nAssistant: {turn['system']['text']}"
    #                 for turn in chat_history
    #             ])
    # else:
    #     chat_history_string = ""
    chat_history_string = helper.prepare_chat_history_string(chat_history)

    # Step 2: Function calling if portfolio or hybrid
    llm = GeminiClient()

    try:
        if intent == "portfolio":
            logger.info(f"Function calling triggered for portfolio intent | Query: {user_query}")
            fn_result = llm.function_call(user_query, PORTFOLIO_FUNCTION_SCHEMA, constant.portfolio_functioncalling_prompt, entities, chat_history_string)

            if fn_result["status"] == "success":
                execution_plan["function_calls"] = fn_result["function_calls"]
            else:
                # 3. Rule-based fallback if entities are present
                if entities and len(entities) > 0:
                    logger.warning("LLM did not return valid function calls. Falling back to rule-based function calling.")
                    fallback_call = rule_based_function_call(user_query, entities)
                    if fallback_call["name"] != "no_function_call":
                        execution_plan["function_calls"] = [fallback_call]
                    else:
                        logger.warning(f"No fallback function could be inferred for query: {user_query}")
                else:
                    logger.warning(f"No valid function calls returned: {fn_result}")


        elif intent == "hybrid":
            logger.info(f"Hybrid intent detected — portfolio + market")
            fn_result = llm.function_call(user_query, PORTFOLIO_FUNCTION_SCHEMA, constant.portfolio_functioncalling_prompt, entities, chat_history_string)

            
            if fn_result["status"] == "success":
                execution_plan["function_calls"] = fn_result["function_calls"]

            else:
                if entities and len(entities) > 0:
                    logger.warning("LLM did not return valid function calls. Falling back to rule-based function calling.")
                    fallback_call = rule_based_function_call(user_query, entities)
                    if fallback_call["name"] != "no_function_call":
                        execution_plan["function_calls"] = [fallback_call]
                    else:
                        logger.warning(f"No fallback function could be inferred for query: {user_query}")
                else:
                    logger.warning(f"No valid function calls returned: {fn_result}")

        logger.info(f"Final execution plan: {execution_plan}")
        return execution_plan

    except Exception as e:
        logger.error(f"Planning failed: {e}", exc_info=True)
        return {
            "intent": intent,
            "entities": entities,
            "confidence": classification_result.get("confidence", 0),
            "agents": [],
            "error": str(e)
        }

def rule_based_function_call(query: str, entities: list[str]) -> dict:
    """
    Simple rule-based fallback for function calling
    if LLM fails to return a valid function.
    """
    q = query.lower().strip()

    # 1. Comparison-type queries
    if len(entities) >= 2 and re.search(constant.comparison_based_pattern, q):
        return {
            "name": "compare_performance",
            "arguments": {"entities": entities}
        }

    # 2. Returns or performance-type queries
    if re.search(constant.performance_based_pattern, q):
        return {
            "name": "get_returns",
            "arguments": {"entities": entities}
        }

    # 3. Holdings or portfolio check
    if re.search(constant.holding_based_pattern, q):
        return {
            "name": "get_holdings",
            "arguments": {}
        }

    # 4. Allocation keywords
    if "allocation" in q and "sector" in q:
        return {"name": "get_allocation", "arguments": {"type": "sector"}}
    if "allocation" in q:
        return {"name": "get_allocation", "arguments": {"type": "asset_class"}}

    # 5. Default fallback if entities exist but nothing matches
    if len(entities) > 0:
        return {
            "name": "get_returns",
            "arguments": {"entities": entities}
        }

    # 6. Absolute fallback
    return {"name": "no_function_call", "arguments": {}}