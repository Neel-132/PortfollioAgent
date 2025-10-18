import backend.utils.helper as helper
import logging
from typing import Dict, List, Optional
import re
from ..utils.gemini_client import GeminiClient

logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def rule_based_classify(query: str, portfolio_keywords: list[str], market_keywords: list[str],  query_confidence_map, symbol_name_map: Optional[Dict[str, List[str]]] = None) -> Dict:
    try:
        if not isinstance(query, str):
            raise TypeError("Query should be a string")
        query_lower = query.lower()
        portfolio_hit = any(word in query_lower for word in portfolio_keywords)
        market_hit = any(word in query_lower for word in market_keywords)

        if portfolio_hit and market_hit:
            intent = "hybrid"; confidence = query_confidence_map["hybrid"]
        elif portfolio_hit:
            intent = "portfolio"; confidence = query_confidence_map["portfolio"]
        elif market_hit:
            intent = "market"; confidence = query_confidence_map["market"]
        else:
            intent = "unknown"; confidence = query_confidence_map["unknown"]

        # Entity detection
        
        portfolio_specific_entities = helper.extract_portfolio_entities(query, symbol_name_map = symbol_name_map)
        spacy_specific_entities = helper.extract_entities_spacy(query)


        entities = list(set(portfolio_specific_entities + spacy_specific_entities))

        normalized_entities = helper.normalize_entities(entities, symbol_name_map)

        if len(normalized_entities) == 0:
            confidence = 0.5

        logger.info(f"Entities detected for the query: {entities}")

        return {
            "intent": intent,
            "entities": list(set(entities)),
            "confidence": confidence
        }

    except Exception as e:
        logger.error(f"Error in rule_based_classify: {e}")
        return {
            "intent": "unknown",
            "entities": [],
            "confidence": query_confidence_map["unknown"]
        }


def llm_classify(prompt: str, symbol_map: Dict[str, list], query: str, previous_conversation: Optional[list] = None) -> Optional[Dict]:
    """
    Uses Gemini to classify query into intent and extract entities,
    with access to symbol map and previous conversation history.
    """
    logger.info(f"🧠 LLM-based classification triggered for query: {query}")

    try:
        # Build conversation history string
        # history_str = ""
        # if previous_conversation:
        #     history_str = "\n".join([
        #         f"User: {turn['user']['text']}\nAssistant: {turn['system']['text']}"
        #         for turn in previous_conversation
        #     ])
        # else:
        #     history_str = ""
        history_str = helper.prepare_chat_history_string(previous_conversation)
        # Build symbol map JSON string
        symbol_map_str = str(symbol_map)

        # Format full prompt
        full_prompt = (
            f"{prompt}\n\n"
            f"SYMBOL_NAME_MAP_JSON:\n{symbol_map_str}\n\n"
            f"CONVERSATION_HISTORY:\n{history_str}\n\n"
            f"User Query: {query}"
        )

        llm = GeminiClient()
        result = llm.generate_text(full_prompt, parse_json=True)

        # Handle invalid or empty responses
        if not result or "intent" not in result:
            logger.warning(f"⚠️ LLM classification returned invalid or empty response: {result}")
            return {
                "intent": "unknown",
                "entities": [],
                "confidence": 0.0
            }

        logger.info(f"✅ LLM classification result: {result}")

        return {
            "intent": result.get("intent", "unknown"),
            "entities": result.get("entities", []),
            "confidence": result.get("confidence", 0.0)
        }

    except Exception as e:
        logger.error(f"❌ LLM classification failed: {e}", exc_info=True)
        return {
            "intent": "unknown",
            "entities": [],
            "confidence": 0.0
        }


    
