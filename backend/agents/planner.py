# agents/planner.py

import logging
from typing import Dict
from ..utils.planner_utils import generate_execution_plan, process_planning
import backend.constant as constant

logger = logging.getLogger(__name__)

class PlannerAgent:
    """
    PlannerAgent delegates planning logic to planner_utils.
    Decides which downstream agents to invoke based on query classification.
    """

    def __init__(self):
        logger.debug("PlannerAgent initialized.")
        self.routing_table = constant.routing_map

    def plan(self, classification_result: Dict, user_query, session) -> Dict:
        """
        Generates an execution plan for the given classification result.
        """
        logger.info(f"PlannerAgent received classification: {classification_result}")

        try:
            execution_plan = process_planning(classification_result, self.routing_table, user_query, session)
            logger.info(f"Execution plan generated: {execution_plan}")
            return execution_plan

        except Exception as e:
            logger.error(f"PlannerAgent failed to generate plan: {e}", exc_info=True)
            return {
                "intent": classification_result.get("intent", "unknown"),
                "entities": classification_result.get("entities", []),
                "confidence": classification_result.get("confidence", 0),
                "agents": [],
                "error": str(e)
            }
