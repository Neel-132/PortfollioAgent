import logging
from typing import Dict, Any
from backend.utils.gemini_client import GeminiClient
import backend.constant as constant

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def build_validator_prompt(original_query: str, workflow_steps: Dict[str, Any]) -> str:
    """
    Build the structured Validator prompt for the LLM to analyze all agents’ steps,
    detect potential logical or factual inconsistencies, and decide whether to re-run any agent.
    """
    try:
        prompt = constant.validator_prompt

        formatted_prompt = (
            prompt
            .replace("{{ORIGINAL_QUERY}}", original_query)
            .replace("{{WORKFLOW_STEPS}}", str(workflow_steps))
        )

        logger.debug("Successfully built validator prompt.")
        return formatted_prompt

    except Exception as e:
        logger.error(f"Error while building validator prompt: {e}", exc_info=True)
        raise


def run_validation(original_query: str, workflow_steps: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes LLM-based validation logic:
    - The LLM acts as a judge, reviewing the workflow steps from all agents.
    - It checks if each agent’s output is coherent and complete.
    - If a failure is detected, it returns the failing agent name and reason.

    Expected JSON structure from LLM:
    {
        "validation_result": "pass" | "fail",
        "failed_agent": "PlannerAgent",
        "reason": "Execution plan missing portfolio agent for a portfolio intent query."
    }
    """
    try:
        # Build structured prompt
        prompt = build_validator_prompt(original_query, workflow_steps)
        llm = GeminiClient()
  
        result = llm.generate_text(prompt, parse_json=True)
        
        # Ensure valid structure
        if not isinstance(result, dict):
            logger.warning(f"Validator returned invalid or non-JSON response: {result}")
            return {"validation_result": "pass", "failed_agent": None, "reason": None}

        validation_result = result.get("validation_result", "pass").lower()

        # Normalize and sanitize fields
        if validation_result not in ("pass", "fail"):
            logger.warning(f"Unexpected validation result: {validation_result}")
            validation_result = "pass"

        structured_output = {
            "validation_result": validation_result,
            "failed_agent": result.get("failed_agent"),
            "reason": result.get("reason"),
        }

        logger.info(f"Validator LLM result: {structured_output}")
        return structured_output

    except Exception as e:
        logger.error(f"Validator execution failed: {e}", exc_info=True)
        # Fail-safe fallback: Never break the pipeline due to validation
        return {
            "validation_result": "pass",
            "failed_agent": None,
            "reason": str(e)
        }
