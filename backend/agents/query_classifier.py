# agents/query_classifier.py

import re
import logging
from typing import Dict, List, Optional
import backend.constant as constant
from backend.utils.query_classification_utils import rule_based_classify, llm_classify


# Initialize logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configure logging format
logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s')

class QueryClassificationAgent:
    def __init__(self, llm_confidence_threshold: float = 0.7):
        self.portfolio_keywords = constant.portfolio_keywords
        self.market_keywords = constant.market_keywords
        self.llm_confidence_threshold = llm_confidence_threshold
        self.query_confidence_map = constant.query_confidence_map

    def classify(
        self, 
        query: str, 
        chat_history:dict,
        symbol_name_map: Optional[Dict[str, List[str]]] = None
    ) -> Dict:
        """
        Classifies query using rules, falls back to LLM if needed.
        """
        logger.info(f"🧠 Classifying query: {query}")
        logger.debug(f"Symbol name map provided: {bool(symbol_name_map)}")

        # STEP 1: Rule-based classification
        result = self._rule_based_classify(query, symbol_name_map)
        logger.debug(f"Rule-based classification result: {result}")

        # STEP 2: Fallback to LLM if needed
        if result["intent"] == "unknown" or result["confidence"] < self.llm_confidence_threshold:
            logger.info(f"Triggering LLM fallback for query: '{query}'")
            llm_result = self._llm_classify(symbol_name_map, query, chat_history)

            if llm_result and llm_result.get("intent") != "unknown":
                logger.debug(f"LLM classification result: {llm_result}")
                result = llm_result
            else:
                logger.warning(f"LLM fallback returned None or unknown for query: '{query}'")

        logger.info(f"✅ Final classification result: {result}")
        return result

    def _rule_based_classify(
        self, 
        query: str, 
        symbol_name_map: Optional[Dict[str, List[str]]] = None
    ) -> Dict:
        """
        Rule-based classification: fast and deterministic.
        """
        logger.debug(f"Running rule-based classification for: {query}")
        result = rule_based_classify(
            query, 
            self.portfolio_keywords, 
            self.market_keywords, 
            self.query_confidence_map,
            symbol_name_map=symbol_name_map
        )
        return result

    def _llm_classify(self, symbol_name_map, query: str, chat_history:dict) -> Optional[Dict]:
        """
        Placeholder for LLM-based classification.
        """
        logger.debug(f"LLM fallback placeholder hit for query: {query}")
        prompt = constant.query_classification_prompt
        return llm_classify(prompt, symbol_name_map, query, chat_history)
