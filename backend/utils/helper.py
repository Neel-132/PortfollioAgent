import pandas as pd
import logging
from typing import Dict, List, Optional, Any
import re
import spacy
import backend.constant as constant
_nlp = spacy.load("en_core_web_lg")
logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def strip_common_suffixes(name: str) -> str:
    """
    Removes common corporate suffixes from a company name.
    Example: "Tesla Inc" -> "Tesla"
    """
    # Split into words and remove trailing suffixes if matched
    parts = name.lower().split()
    while parts and parts[-1] in constant.COMMON_SUFFIXES:
        parts.pop()
    return " ".join(parts).strip()

def build_reverse_symbol_map(symbol_map: Dict[str, List[str]]) -> Dict[str, str]:
    """
    Builds a reverse mapping from name variations to ticker symbols.

    Args:
        symbol_map: dict of ticker -> list of name variations

    Returns:
        reverse_map: dict of name variation -> ticker
    """
    reverse_map = {}
    for ticker, variations in symbol_map.items():
        for variant in variations:
            # store lowercase for matching
            variant = variant.strip().lower()
            if variant and variant not in reverse_map:
                reverse_map[variant] = ticker
    return reverse_map

def create_stock_mappings(holdings, include_variations=False):
    """
    Creates a mapping from symbol to name variations to aid in entity normalization.
    - Handles common suffix stripping (Inc, Corp, etc.)
    - Optionally adds tokenized variations.
    """
    try:
        symbol_map = {}
        if not isinstance(holdings, list):
            return {}

        for item in holdings:
            symbol = item.get("symbol", "").strip()
            raw_name = item.get("security_name", "").strip()

            if not symbol or not raw_name:
                continue

            normalized_name = raw_name.lower()
            stripped_name = strip_common_suffixes(normalized_name)

            variations = {normalized_name}

            # Add stripped suffix version if different
            if stripped_name and stripped_name != normalized_name:
                variations.add(stripped_name)

            # Optional tokenization for flexible matching
            if include_variations:
                tokens = [t for t in stripped_name.split() if len(t) > 2]
                variations.update(tokens)

            symbol_map[symbol] = list(variations)
        
        return symbol_map

    except Exception as e:
        logger.error(f"Error in create_stock_mappings: {str(e)}", exc_info=True)
        return {}
    
def extract_portfolio_entities(
        query: str, 
        symbol_name_map: Optional[Dict[str, List[str]]] = None
    ) -> List[str]:
        try:
            """
            Extracts entities from query using:
            - Direct ticker symbol match (e.g. NVDA)
            - Name match against symbol_name_map (e.g. Nvidia → NVDA)
            """
            query_lower = query.lower()

            # 1. Direct ticker detection (e.g. NVDA, MSFT)
            detected_entities = re.findall(r"\b[A-Z]{2,5}\b", query)

            # 2. Name matching (e.g. Nvidia, Microsoft)
            if symbol_name_map:
                ## only filtering entities (in caps) iff they are present in symbol_name_map
                detected_entities = [item for item in detected_entities if item in symbol_name_map]
                for symbol, name_variants in symbol_name_map.items():
                    for variant in name_variants:
                        if variant in query_lower:
                            if symbol not in detected_entities:
                                detected_entities.append(symbol)


                return list(set(detected_entities))
            else:
                logger.info("No symbol_name_map provided for portfolio entity extractor. Hence, returning empty list")
                return []
        except Exception as e:
            logger.error(f"Error in extract_portfolio_entities: {str(e)}")
            return []
        
def extract_entities_spacy(text: str) -> List[str]:
    """
    Extract named entities from text using spaCy en_core_web_lg model.

    Currently extracts:
    - ORG (Organizations / Companies)
    - PRODUCT (ETFs, financial products)
    - GPE (Geopolitical Entities - optional)

    Returns a list of unique entity strings.
    """
    try:
        doc = _nlp(text)
        extracted = []

        for ent in doc.ents:
            if ent.label_ in constant.spacy_valid_labels:
                extracted.append(ent.text.strip())

        # Deduplicate and normalize
        return list(set(extracted))
    except Exception as e:
        logger.error(f"Error in extract_entities_spacy: {str(e)}")
        return []
    

def build_execution_result(
    classification: Optional[Dict[str, Any]],
    plan: Optional[Dict[str, Any]],
    portfolio_resp: Optional[Dict[str, Any]],
    market_resp: Optional[Dict[str, Any]],
    session: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Merge agent outputs into a single execution_result for ResponseGenerator.

    Schema:
    {
      "intent": "portfolio" | "market" | "hybrid" | "unknown",
      "entities": [...],
      "portfolio": { ... } | None,
      "market": { ... } | None
    }
    """
    classification = classification or {}
    plan = plan or {}
    portfolio_resp = portfolio_resp or {}
    market_resp = market_resp or {}
    session = session or {}

    # Unwrap market agent payload: it returns {"status", "entities", "market_data": {...}}
    market_section = None
    if market_resp and market_resp.get("status") == "success":
        market_section = market_resp.get("market_data") or {}

    portfolio_section = None
    if portfolio_resp and portfolio_resp.get("status") == "success":
        portfolio_section = portfolio_resp

    return {
        "intent": classification.get("intent", plan.get("intent", "unknown")),
        "entities": plan.get("entities") or classification.get("entities") or [],
        "portfolio": portfolio_section,
        "market": market_section,
        "session": session
    }

def normalize_entities(
    extracted_entities: List[str],
    symbol_map: Dict[str, List[str]]
) -> List[str]:
    """
    Normalizes extracted entities to valid stock tickers using:
    1. Direct ticker match
    2. Reverse name lookup (via generated reverse map)

    Args:
        extracted_entities: raw entities extracted from query (e.g. ['Tesla', 'MSFT'])
        symbol_map: ticker -> list of name variations

    Returns:
        List of normalized tickers (e.g. ['TSLA', 'MSFT'])
    """
    normalized = set()
    reverse_map = build_reverse_symbol_map(symbol_map)

    for entity in extracted_entities:
        if not entity:
            continue
        e = entity.strip().lower()

        # 1. Direct ticker match
        if e.upper() in symbol_map:
            normalized.add(e.upper())
            continue

        # 2. Reverse name lookup
        if e in reverse_map:
            normalized.add(reverse_map[e])
            continue

    if not normalized and extracted_entities:
        logger.warning(f"Entity normalization failed for: {extracted_entities}")

    return list(normalized)


def escape_markdown(text):
    """Escape special markdown characters to display as literal text"""
    # Characters that need escaping in markdown
    special_chars = ['\\', '`', '*', '_', '{', '}', '[', ']', '(', ')', '#', '+', '-', '.', '!', '$']
    
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    
    return text

def escape_dollar_signs(text):
    """Escape dollar signs for Streamlit markdown rendering while preserving markdown syntax"""
    # Replace single $ with \$ to prevent LaTeX rendering
    # But avoid replacing $$ (which is intentional LaTeX)
    text = re.sub(r'\$(?!\$)', r'\\$', text)
    return text

def prepare_chat_history_string(chat_history):
    if len(chat_history) > 0:
        chat_history_string = "\n".join([
                    f"User: {turn['user']['text']}\nAssistant: {turn['system']['text']}"
                    for turn in chat_history
                ])
    else:
        chat_history_string = ""
    return chat_history_string

def extract_all_stock_entities(classification_result):
    try:
        """
        Extract all stock ticker entities from the new classification format
        and return them as a single flat list.
        """
        all_tickers = []
        
        # Extract from current query entities
        if "entities" in classification_result and "stocks" in classification_result["entities"]:
            for stock in classification_result["entities"]["stocks"]:
                if isinstance(stock, dict) and "ticker" in stock:
                    ticker = stock["ticker"]
                    # Skip unresolved entities
                    if ticker != "UNRESOLVED":
                        all_tickers.append(ticker)
                elif isinstance(stock, str):
                    # Handle case where stock is just a string ticker
                    all_tickers.append(stock)
        
        # Extract from context entities
        if "context_entities" in classification_result and "stocks" in classification_result["context_entities"]:
            for stock in classification_result["context_entities"]["stocks"]:
                if isinstance(stock, dict) and "ticker" in stock:
                    ticker = stock["ticker"]
                    if ticker != "UNRESOLVED":
                        all_tickers.append(ticker)
                elif isinstance(stock, str):
                    all_tickers.append(stock)
        
        # Deduplicate while preserving order
        seen = set()
        unique_tickers = []
        for ticker in all_tickers:
            if ticker not in seen:
                seen.add(ticker)
                unique_tickers.append(ticker)
        
        
        entity_dict = classification_result.get("entities", {}).copy()
        entity_dict['stocks'] = unique_tickers
        return unique_tickers, entity_dict, classification_result.get("metadata", {})

    except Exception as e:
        logger.error(f"Failed to extract stock entities: {e}", exc_info=True)
        return [], {}, {}


def initialize_workflow_log(state: Dict, original_query: str) -> None:
    """
    Initialize workflow log structure at the start of execution.
    """
    state["workflow_log"] = {
        "original_query": original_query,
        "agents_executed": [],
        "steps": []
    }
    logger.info("Workflow log initialized")


def log_agent_step(state: Dict, agent_name: str, agent_input: Any, agent_output: Any) -> None:
    """
    Append a new step to the workflow log.
    """
    try:
        if "workflow_log" not in state:
            initialize_workflow_log(state, state.get("query", ""))

        state["workflow_log"]["agents_executed"].append(agent_name)
        state["workflow_log"]["steps"].append({
            "agent": agent_name,
            "input": agent_input,
            "output": agent_output
        })

        logger.info(f"Logged step for agent: {agent_name}")

    except Exception as e:
        logger.error(f"Failed to log workflow step for {agent_name}: {e}", exc_info=True)


def get_workflow_log(state: Dict) -> Dict:
    """
    Safely retrieve the workflow log from state.
    """
    return state.get("workflow_log", {})

