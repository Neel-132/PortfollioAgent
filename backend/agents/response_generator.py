import logging
from typing import Dict, Any
from ..utils.response_generator_utils import generate_natural_language_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configure logging format
logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s')

class ResponseGeneratorAgent:
    """
    ResponseGeneratorAgent
    -----------------------
    Orchestrates the response generation process.
    Delegates actual LLM / text generation logic to response_generator_utils.
    """

    def __init__(self):
        logger.debug("ResponseGeneratorAgent initialized.")

    def run(self, query: str, execution_result: Dict[str, Any], session: Dict) -> Dict[str, Any]:
        """
        Entry point for generating final user-facing response.
        Returns both natural language text and structured data.
        """
        logger.info(f"Running ResponseGeneratorAgent for query: {query}")

        try:
            chat_history = session.get("chat_history", [])
            response = generate_natural_language_response(query, execution_result, chat_history)
            logger.info("Response successfully generated.")
            logger.debug(f"Generated response: {response}")
            return response

        except Exception as e:
            logger.error(f"ResponseGeneratorAgent failed: {e}", exc_info=True)
            return {
                "text": "Sorry, I couldn’t generate a response for this query.",
                "data": execution_result,
                "error": str(e)
            }
