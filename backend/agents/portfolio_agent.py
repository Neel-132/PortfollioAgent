# agents/portfolio_agent.py

import logging
from typing import Dict
from backend.utils.portfolio_utils import process_portfolio_query

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Configure logging format
logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s')

class PortfolioAgent:
    """
    PortfolioAgent handles all portfolio-related queries:
    - Full portfolio breakdown
    - Individual stock performance
    - Total allocations, returns, etc.
    """

    def __init__(self):
        logger.debug("📌 PortfolioAgent initialized.")

    def run(self, execution_plan: Dict, session: Dict, client_id:str) -> Dict:
        """
        Executes portfolio-related query based on execution plan and session state.
        """
        entities = execution_plan.get("entities", [])

        logger.info(
            f"📊 PortfolioAgent invoked | "
            f"client_id={client_id} | intent={execution_plan.get('intent')} | entities={entities}"
        )

        try:
            response = process_portfolio_query(execution_plan, session, client_id)
        
            if response.get("status") == "success":
                logger.info(
                    f"✅ PortfolioAgent processed query for client_id={client_id} "
                    f"with {response.get('total_holdings', 0)} holdings"
                )
            elif response.get("status") == "not_found":
                logger.warning(
                    f"⚠️ PortfolioAgent: No matching holdings found "
                    f"for client_id={client_id}, entities={entities}"
                )
            else:
                logger.error(
                    f"❌ PortfolioAgent returned error for client_id={client_id}: "
                    f"{response.get('message', 'Unknown error')}"
                )

            logger.debug(f"Response payload: {response}")
            return response

        except Exception as e:
            logger.error(
                f"❌ PortfolioAgent failed for client_id={client_id}: {e}",
                exc_info=True
            )
            return {
                "status": "error",
                "message": str(e),
                "entities": entities
            }
