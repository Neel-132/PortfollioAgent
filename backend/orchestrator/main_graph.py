import logging
from typing import Dict
from langgraph.graph import StateGraph, END

from backend.agents.query_classifier import QueryClassificationAgent
from backend.agents.planner import PlannerAgent
from backend.agents.portfolio_agent import PortfolioAgent
from backend.agents.market_agent import MarketAgent
from backend.agents.validator import ValidatorAgent
from backend.agents.response_generator import ResponseGeneratorAgent
from backend.managers.dependency_loader import DependencyLoader
from backend.managers.memory_manager import MemoryManager
import backend.utils.helper as helper

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# 1. Define the shared state schema
def initial_state(query: str, client_id: str, session_id: str, previous_session=None) -> Dict:
    if previous_session is None:
        loader = DependencyLoader()
        session = loader.load_client_dependencies(client_id, session_id)
    else:
        session = previous_session.copy()
    return {
        "query": query,
        "client_id": client_id,
        "session_id": session_id,
        "session": session,
        "classification": {},
        "execution_plan": {},
        "response": {},
        "market_data": {},
        "final_response": {}
    }


# 2. Query Classification Node
def classify_query(state: Dict) -> Dict:
    client_id = state["client_id"]
    session_id = state["session_id"]
    query = state["query"]

    logger.info(f"[Classifier] client_id={client_id}, session_id={session_id}, query='{query}'")
    symbol_name_map = state["session"].get("symbol_name_map", {})
    chat_history = state["session"].get("chat_history", {})
    classifier = QueryClassificationAgent()
    classification = classifier.classify(query, chat_history, symbol_name_map = symbol_name_map)

    classification_to_log = classification.copy()
    if 'confidence' in classification_to_log:
        del classification_to_log['confidence']
    helper.log_agent_step(state, "QueryClassificationAgent", query, classification_to_log)

    logger.info(f"[Classifier] Classification result: {classification}")
    state["classification"] = classification
    return state


# 3. Planner Node
def planner_node(state: Dict) -> Dict:
    client_id = state["client_id"]
    planner = PlannerAgent()
    execution_plan = planner.plan(state["classification"], state["query"], state["session"])
    helper.log_agent_step(state, "PlannerAgent", state["classification"], execution_plan)
    logger.info(f"[Planner] Execution plan for client_id={client_id}: {execution_plan}")
    state["execution_plan"] = execution_plan
    return state


# 4. Market Agent Node
def market_node(state: Dict) -> Dict:
    client_id = state["client_id"]
    agent = MarketAgent()
    response = agent.run(state["execution_plan"], state["session"])

    helper.log_agent_step(
            state=state,
            agent_name="MarketAgent",
            agent_input=state["execution_plan"],
            agent_output=response
        )
    
    logger.info(f"[MarketAgent] client_id={client_id} | status={response.get('status')}")
    state["market_data"] = response
    return state


# 5. Portfolio Agent Node
def portfolio_node(state: Dict) -> Dict:
    client_id = state["client_id"]
    agent = PortfolioAgent()
    response = agent.run(state["execution_plan"], state["session"], state["client_id"])
    helper.log_agent_step(state, "PortfolioAgent", state["execution_plan"], response)
    logger.info(f"[PortfolioAgent] client_id={client_id} | status={response.get('status')}")
    state["response"] = response
    return state

def validator_node(state: Dict) -> Dict:
    """
    Runs the ValidatorAgent after all planned agents have executed.
    Uses the logged workflow steps to check if any agent's output was faulty.
    If a failure is detected, returns that information for retry logic.
    """
    try:
        client_id = state["client_id"]
        original_query = state.get("query", "")
        workflow_log = helper.get_workflow_log(state)

        logger.info(f"[Validator] Running validator for client_id={client_id}")

        validator = ValidatorAgent()
        validation_result = validator.run(original_query, workflow_log)

        state["validation_result"] = validation_result

        if validation_result.get("validation_result") == "fail":
            failed_agent = validation_result.get("failed_agent")
            reason = validation_result.get("reason")
            logger.warning(
                f"[Validator] Validation failed | failed_agent={failed_agent} | reason={reason}"
            )
        else:
            logger.info(f"[Validator] Validation passed for client_id={client_id}")

        return state

    except Exception as e:
        logger.error(f"[Validator] Exception occurred: {e}", exc_info=True)
        state["validation_result"] = {
            "validation_result": "error",
            "failed_agent": None,
            "reason": str(e)
        }
        return state


# 6. Response Generator Node
def response_generator_node(state: Dict) -> Dict:
    client_id = state["client_id"]
    agent = ResponseGeneratorAgent()

    logger.info(f"[ResponseGenerator] Generating final response for client_id={client_id}")
    execution_result = helper.build_execution_result(
        classification=state.get("classification"),
        plan=state.get("execution_plan"),
        portfolio_resp=state.get("response"),
        market_resp=state.get("market_data"),
        session = state.get("session")
    )
    

    # ResponseGeneratorAgent.run expects: run(query: str, execution_result: Dict)
    final_response = agent.run(state["query"], execution_result, state.get("session", {}))

    helper.log_agent_step(
            state=state,
            agent_name="ResponseGeneratorAgent",
            agent_input=execution_result,
            agent_output=final_response
        )

    state["final_response"] = final_response
    return state

# 7. Final Response Node (END)
def response_node(state: Dict) -> Dict:
    client_id = state["client_id"]
    logger.info(f"[Response] Final response ready for client_id={client_id}")
    return state


# 8. Build the Graph
def build_graph():
    graph = StateGraph(dict)

    graph.add_node("classifier", classify_query)
    graph.add_node("planner", planner_node)
    graph.add_node("market", market_node)
    graph.add_node("portfolio", portfolio_node)
    graph.add_node("response_generator", response_generator_node)
    graph.add_node("response", response_node)
    graph.add_node("validator", validator_node)    

    graph.set_entry_point("classifier")
    graph.add_edge("classifier", "planner")

    # Planner routes to market, portfolio, hybrid or end
    graph.add_conditional_edges(
        "planner",
        lambda state: next_node_from_plan(state),
        {
            "MarketAgent": "market",
            "PortfolioAgent": "portfolio",
            "Hybrid": "market",
            "END": "response"
        }
    )

    # Conditional routing from market:
    def next_after_market(state: dict) -> str:
        plan = state.get("execution_plan", {})
        agents = plan.get("agents", []) if plan else []
        return "portfolio" if "PortfolioAgent" in agents else "response_generator"

    graph.add_conditional_edges(
        "market",
        next_after_market,
        {
            "portfolio": "portfolio",
            "response_generator": "response_generator"
        }
    )

    # Portfolio always goes to response generator
    graph.add_edge("portfolio", "response_generator")

    graph.add_edge("response_generator", "validator")

    # ✅ Then move to final response
    graph.add_edge("validator", "response")

    # # Response generator always finishes
    # graph.add_edge("response_generator", "response")
    graph.set_finish_point("response")

    # PortfolioAgent only | classifier → planner → portfolio → response_generator → response  
    # MarketAgent only            | classifier → planner → market → response_generator → response   
    # Hybrid (Market + Portfolio) | classifier → planner → market → portfolio → response_generator → response 

    return graph


# 9. Routing Logic
def next_node_from_plan(state: Dict) -> str:
    plan = state.get("execution_plan", {})
    agents = plan.get("agents", []) if plan else []

    if "MarketAgent" in agents and "PortfolioAgent" in agents:
        return "Hybrid"
    if "MarketAgent" in agents:
        return "MarketAgent"
    if "PortfolioAgent" in agents:
        return "PortfolioAgent"

    logger.warning(f"[Planner] No valid agents to invoke for client_id={state['client_id']}. Ending graph.")
    return "END"


# 10. Helper function to run orchestrator
def run_query(query: str, client_id: str, session_id: str, previous_session: Dict = None):
    graph = build_graph()
    app = graph.compile()
    final_output = {}
    state = initial_state(query, client_id, session_id, previous_session=previous_session)
    final_state = app.invoke(state)
    final_output = {
        "structured_response": final_state.get("response", {}),
        "market_response": final_state.get("market_data", {}),
        "final_response": final_state.get("final_response", {}),
    }
 
    if previous_session is None:
        previous_session = final_state.get("session", {}).copy()
    
    MemoryManager.update_session_memory(previous_session, final_output, query)
    final_output["session"] = previous_session.copy()
    return final_output


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    result = run_query("What's the latest news on Tesla?", "CLT-001", "sess-001")
    print("\nFINAL NATURAL LANGUAGE RESPONSE:\n", result["final_response"].get("text"))
    print("\nFINAL MARKET RESPONSE:\n", result["market_response"])
    print("\nFINAL STRUCTURED RESPONSE:\n", result["structured_response"])
