
import logging
from typing import Dict, Any
from .schemas.input_schema import QueryInput
from .orchestrator.main_graph import run_query
from .managers.dependency_loader import DependencyLoader

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def process_request(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point to process incoming request from UI.
    1. Validate input dictionary using Pydantic schema.
    2. Construct or reuse session data.
    3. Call orchestrator with clean inputs.
    4. Return structured response.
    """
    # 1️. Validate input schema
    try:
        validated_input = QueryInput(**input_data)
    except Exception as e:
        logger.error(f"Input validation failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Invalid input: {str(e)}"
        }

    client_id = validated_input.client_id
    query = validated_input.query
    session_id = validated_input.session_id
    prev_session = validated_input.previous_session

    logger.info(
        f" Received query from client_id={client_id} "
        f"session_id={session_id} | query='{query}'"
    )

    # 2️Construct session state
    if prev_session and prev_session.portfolio:
        logger.info(f" Reusing previous session for client_id={client_id}")
        session = {
            "client_id": client_id,
            "portfolio": prev_session.portfolio,
            "chat_history": prev_session.chat_history or [],
            "intermediate_results": prev_session.intermediate_results or {},
            "metadata": prev_session.metadata or {},
        }
    else:
        logger.info(f"No previous session found. Loading portfolio for {client_id}")
        loader = DependencyLoader()
        session = loader.load_client_dependencies(client_id, session_id)

    # 3️Pass clean data to orchestrator
    try:
        response = run_query(query, client_id, session_id, session = session)
        logger.info(f"Query processed successfully for client_id={client_id}")
        return response
    except Exception as e:
        logger.error(f"Failed to process query: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Processing failed: {str(e)}"
        }


if __name__ == "__main__":
    response = process_request({
        "client_id": "CLT-010",
        "query": "What is the impact of the Microsoft & OpenAI deal on my portfolio?",
        "metadata": {},
        "previous_session": None
    })
    print("\nFINAL RESPONSE:\n", response['final_response']['text'])
