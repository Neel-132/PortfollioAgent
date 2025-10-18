import logging
from typing import Dict
from backend.utils.market_utils import process_market_query

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class MarketAgent:
    """
    MarketAgent handles market-related queries such as:
    - Fetching cached news and SEC filings
    - Fetching latest stock prices
    - Summarizing market context for relevant entities
    """

    def __init__(self):
        logger.debug("MarketAgent initialized.")

    def run(self, execution_plan: Dict, session: Dict) -> Dict:
        """
        Executes market-related query.
        """
        try:
            entities = execution_plan.get("entities", [])
            if not entities:
                logger.warning("MarketAgent invoked but no entities provided in execution plan.")

            response = process_market_query(entities, session)
            logger.info(f"MarketAgent successfully processed {len(entities)} entities.")
            logger.debug(f"MarketAgent response: {response}")

            return {
                "status": "success",
                "entities": entities,
                "market_data": response
            }

        except Exception as e:
            logger.error(f"MarketAgent failed: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "entities": execution_plan.get("entities", [])
            }
