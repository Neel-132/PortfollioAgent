import logging
from typing import Dict, Any
from backend.utils import validation_utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ValidatorAgent:
    """
    ValidatorAgent inspects the workflow log to check whether each agent
    produced coherent, non-empty, and logically valid outputs.
    If it detects a failure, it returns the agent name and reason so that
    the graph can retry execution from that point.
    """

    def __init__(self):
        logger.debug("ValidatorAgent initialized")

    def run(self, query: str, workflow_log: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info("[ValidatorAgent] Starting validation")
            result = validation_utils.run_validation(query, workflow_log)

            if result["validation_result"] == "fail":
                logger.warning(
                    f"[ValidatorAgent] Validation failed for agent={result.get('failed_agent')} "
                    f"| reason={result.get('reason')}"
                )
            else:
                logger.info("[ValidatorAgent] Validation passed")

            return result

        except Exception as e:
            logger.error(f"[ValidatorAgent] Unexpected error: {e}", exc_info=True)
            return {
                "validation_result": "error",
                "failed_agent": None,
                "reason": str(e)
            }
