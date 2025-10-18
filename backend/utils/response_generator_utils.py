import json
import logging
from typing import Dict, Any
from ..utils.gemini_client import GeminiClient
import backend.constant as constant
import backend.utils.helper as helper
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def generate_natural_language_response(query: str, execution_result: Dict[str, Any], chat_history:dict[Any]) -> Dict[str, Any]:
    """
    Core logic for transforming structured execution results into natural language
    using Gemini LLM.
    """
    portfolio_data = execution_result.get("portfolio", None) 
    market_data = execution_result.get("market", None) 
    if not portfolio_data and not market_data:
        logger.warning("No portfolio or market data found in execution result.")
        return {
            "text": "Sorry, I couldn't process your request.",
            "data": execution_result
        }
    
        # if len(chat_history) > 0:
        #     chat_history_string = "\n".join([
        #                 f"User: {turn['user']['text']}\nAssistant: {turn['system']['text']}"
        #                 for turn in chat_history
        #             ])
        # else:
        #     chat_history_string = ""
    chat_history_string = helper.prepare_chat_history_string(chat_history)
    
    llm = GeminiClient()
    

   

    llm_prompt = f"""
    {constant.response_generation_prompt}

    User Query:
    {query}
    Conversation History:
    {chat_history_string}
    Portfolio Data:
    {portfolio_data if portfolio_data else "No portfolio data provided."}

    Market Data:
    {market_data if market_data else "No market data provided."}


    Write a natural language response:
    """

    logger.debug(f"Prompt to LLM: {llm_prompt}")

    try:
        text_response = llm.generate_text(llm_prompt)
        logger.info("Successfully generated LLM response.")
        return {
            "text": text_response,
            "data": execution_result
        }

    except Exception as e:
        logger.error(f"LLM response generation failed: {e}", exc_info=True)
        return {
            "text": "I processed your request successfully, but couldn’t generate a natural language response.",
            "data": execution_result,
            "error": str(e)
        }
