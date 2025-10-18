import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

def truncate_list(items: List, max_length: int = 10) -> List:
    return items[-max_length:] if len(items) > max_length else items

class MemoryManager:
    @staticmethod
    def update_session_memory(session: Dict[str, Any], result: Dict[str, Any], query: str, max_context = 5) -> Dict[str, Any]:
        """
        Update the backend session object with new memory after each interaction.
        Returns the updated session dictionary.
        """
        # 1. Conversations
        debug_data = {
            "query": query,
            "structured_response": result["final_response"].get("data", {}).get("portfolio", {}),
            "market_response": result["final_response"].get("data", {}).get("market_response", {}),
        }
        conversion_dict = {}
        conversion_dict['user'] = {"role": "user", "text": query}
        conversion_dict['system'] = {
            "role": "assistant",
            "text": result["final_response"].get("text", "Sorry, I couldn't process that."),
            "debug_data": debug_data
        }
        session.setdefault("chat_history", [])
        
        session["chat_history"] = truncate_list(session["chat_history"], max_context)

        logger.info(f"Memory updated for backend session: {session.get('session_id', 'unknown')}")
        return session

    @staticmethod
    def build_session_payload(session: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not session:
            return None
        return {
            "previous_conversations": session.get("previous_conversations", []),
            "last_portfolio": session.get("last_portfolio", {}),
            "last_market": session.get("last_market", {}),
            "intermediate_results": session.get("intermediate_results", {}),
            "agent_context": session.get("agent_context", {}),
            "metadata": session.get("metadata", {}),
        }

    @staticmethod
    def clear_session_memory(session: Dict[str, Any]) -> Dict[str, Any]:
        """Return a clean, empty session dict for reset/logout."""
        cleared = {
            "previous_conversations": [],
            "last_portfolio": {},
            "last_market": {},
            "intermediate_results": {"last_function_calls": []},
            "agent_context": {},
            "metadata": {"query_count": 0},
        }
        logger.info(f"🧹 Cleared session memory for {session.get('client_id', 'unknown')}")
        return cleared
