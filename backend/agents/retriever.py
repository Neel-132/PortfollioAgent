import logging
from typing import Dict, List, Optional
from ..utils.retrieval_utils import get_bge_embedding, search_sec_filings
import backend.constant as constant

logger = logging.getLogger(__name__)

class KnowledgeBaseRetrieverAgent:
    def __init__(self, qdrant_client, collection_name: str):
        self.client = qdrant_client
        self.collection_name = collection_name
        self.top_k = constant.top_k_chunks_to_retrieve

    def run(self, query: str, ticker: Optional[str] = None, filing_type: Optional[str] = None) -> Dict:
        """
        Agent entry point for retrieving context from SEC filings KB.
        Args:
            query (str): User query.
            ticker (str, optional): Ticker symbol for filtering.
            filing_type (str, optional): Filing type (e.g., 10-K).
            top_k (int): Number of results to fetch.

        Returns:
            Dict: Structured retrieval results with metadata and scores.
        """
        try:
            if not query or not isinstance(query, str):
                logger.warning("Empty or invalid query received by KnowledgeBaseRetrieverAgent.")
                return {"status": "failed", "results": [], "error": "Invalid query"}

            # Convert query to embedding
            query_vector = get_bge_embedding(query, is_query=True)
            if len(query_vector) == 0:
                logger.warning("Failed to generate embedding for query.")
                return {"status": "failed", "results": [], "error": "Embedding generation failed"}
            if not query_vector:
                logger.warning("Failed to generate embedding for query.")
                return {"status": "failed", "results": [], "error": "Embedding generation failed"}
            
            query_vector = query_vector[0]

            # Retrieve from Qdrant
            retrieval_results = search_sec_filings(
                client=self.client,
                collection_name=self.collection_name,
                query_vector=query_vector,
                top_k=self.top_k,
                ticker=ticker,
                filing_type=filing_type
            )

            status = "success" if retrieval_results else "empty"
            return {
                "status": status,
                "query": query,
                "ticker": ticker,
                "filing_type": filing_type,
                "results": retrieval_results
            }

        except Exception as e:
            logger.error(f"KnowledgeBaseRetrieverAgent failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "results": [],
                "error": str(e)
            }
