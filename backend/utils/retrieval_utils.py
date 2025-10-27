import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
import backend.constant as constant
from typing import List, Optional, Dict
from qdrant_client.http import models as qmodels
from qdrant_client import QdrantClient
import logging

logger = logging.getLogger(__name__)

# BGE-small model
MODEL_NAME = constant.embedding_model_name
device = "cuda" if torch.cuda.is_available() else "cpu"

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME).to(device)
model.eval()


def get_bge_embedding(texts, is_query=True, as_list=True):
    """
    Generate normalized embeddings for input texts using BGE-small.
    
    Args:
        texts (str or list[str]): Input text(s) to embed.
        is_query (bool): If True, adds "Represent this sentence for searching relevant passages: " 
                        prefix for queries. Set False for passages/documents.
        as_list (bool): If True, return embeddings as Python list; else return torch tensor.
        
    Returns:
        list or torch.Tensor: Embedding(s) for the input text(s).
    """
    if isinstance(texts, str):
        texts = [texts]
    
    # Add instruction prefix for queries (recommended by BGE)
    if is_query:
        instruction = "Represent this sentence for searching relevant passages: "
        texts = [instruction + text for text in texts]
    
    # Tokenize
    encoded_input = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt"
    ).to(device)
    
    # Get embeddings
    with torch.no_grad():
        model_output = model(**encoded_input)
        # Use CLS token embedding (first token)
        embeddings = model_output[0][:, 0]
    
    # Normalize embeddings
    embeddings = F.normalize(embeddings, p=2, dim=1)
    
    if as_list:
        return embeddings.cpu().tolist()
    return embeddings


def batch_encode(texts, batch_size=32, is_query=False, as_list=True):
    """
    Encode texts in batches for better memory efficiency.
    
    Args:
        texts (list[str]): List of texts to embed.
        batch_size (int): Number of texts to process at once.
        is_query (bool): Whether texts are queries or passages.
        as_list (bool): If True, return as Python list; else return torch tensor.
        
    Returns:
        list or torch.Tensor: All embeddings concatenated.
    """
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embeddings = get_bge_embedding(batch, is_query=is_query, as_list=False)
        all_embeddings.append(embeddings)
    
    all_embeddings = torch.cat(all_embeddings, dim=0)
    
    if as_list:
        return all_embeddings.cpu().tolist()
    return all_embeddings


def compute_similarity(query, passages, top_k=5):
    """
    Compute similarity between a query and multiple passages.
    
    Args:
        query (str): Query text.
        passages (list[str]): List of passage texts.
        top_k (int): Number of top results to return.
        
    Returns:
        list[tuple]: List of (index, passage, score) tuples sorted by score.
    """
    # Encode query and passages
    query_embedding = get_bge_embedding(query, is_query=True, as_list=False)
    passage_embeddings = get_bge_embedding(passages, is_query=False, as_list=False)
    
    # Compute cosine similarity
    similarities = (query_embedding @ passage_embeddings.T).squeeze(0)
    
    # Get top-k results
    top_scores, top_indices = torch.topk(similarities, min(top_k, len(passages)))
    
    results = [
        (idx.item(), passages[idx.item()], score.item())
        for idx, score in zip(top_indices, top_scores)
    ]
    
    return results


def search_sec_filings(
    client:QdrantClient,
    collection_name: str,
    query_vector: List[float],
    top_k: int = 5,
    ticker: Optional[str] = None,
    filing_type: Optional[str] = None,
) -> List[Dict]:
    """
    Retrieve top relevant SEC filing chunks from Qdrant based on a query vector and optional filters.

    Args:
        client: Qdrant client instance.
        collection_name (str): Name of the Qdrant collection.
        query_vector (List[float]): Embedding of the user query.
        top_k (int): Number of results to return.
        ticker (str, optional): Filter by ticker symbol.
        filing_type (str, optional): Filter by filing type (e.g., 10-K).

    Returns:
        List[Dict]: List of search results with payload and scores.
    """
    try:
        filters = []
        if ticker:
            filters.append(
                qmodels.FieldCondition(
                    key="ticker",
                    match=qmodels.MatchValue(value=ticker)
                )
            )
        if filing_type:
            filters.append(
                qmodels.FieldCondition(
                    key="filing_type",
                    match=qmodels.MatchValue(value=filing_type)
                )
            )

        filter_obj = qmodels.Filter(must=filters) if filters else None
        
        search_result = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=filter_obj,
            limit=top_k,
            with_payload=True,
            with_vectors=False
        )

        results = [
            {
                "score": point.score,
                "ticker": point.payload.get("ticker"),
                "filing_type": point.payload.get("filing_type"),
                "filing_date": point.payload.get("filing_date"),
                "title": point.payload.get("filing_title"),
                "url": point.payload.get("url"),
                "text": point.payload.get("text")
            }
            for point in search_result
        ]

        return results

    except Exception as e:
        logger.error(f"Qdrant retrieval failed: {e}", exc_info=True)
        return []



# Example usage
if __name__ == "__main__":
    print(f"Using device: {device}")
    print(f"Model: {MODEL_NAME}\n")
    
    # Example 1: Simple embedding
    print("=" * 60)
    print("Example 1: Simple Embedding")
    print("=" * 60)
    sentence = "How is the weather today?"
    embedding = get_bge_embedding(sentence, is_query=True, as_list=False)
    print(f"Text: {sentence}")
    print(f"Embedding shape: {embedding.shape}")
    print(f"First 5 values: {embedding[0][:5].tolist()}\n")
    
    # Example 2: Similarity between sentences
    print("=" * 60)
    print("Example 2: Sentence Similarity")
    print("=" * 60)
    sentences = [
        "How is the weather today?",
        "What is the current weather like today?",
        "I love machine learning",
    ]
    embeddings = get_bge_embedding(sentences, is_query=True, as_list=False)
    
    print("Similarity matrix:")
    for i, sent1 in enumerate(sentences):
        for j, sent2 in enumerate(sentences):
            if i <= j:
                sim = (embeddings[i] @ embeddings[j].T).item()
                print(f"  Sentence {i+1} <-> Sentence {j+1}: {sim:.4f}")
    print()
    
    # Example 3: Query-Passage retrieval
    print("=" * 60)
    print("Example 3: Query-Passage Retrieval")
    print("=" * 60)
    query = "What is machine learning?"
    passages = [
        "Machine learning is a subset of artificial intelligence that focuses on algorithms.",
        "Python is a popular programming language.",
        "Deep learning uses neural networks with multiple layers.",
        "The weather today is sunny and warm.",
        "Machine learning models learn patterns from data."
    ]
    
    results = compute_similarity(query, passages, top_k=3)
    
    print(f"Query: {query}\n")
    print("Top 3 relevant passages:")
    for rank, (idx, passage, score) in enumerate(results, 1):
        print(f"{rank}. [Score: {score:.4f}] {passage}")
    print()
    
    # Example 4: Batch encoding
    print("=" * 60)
    print("Example 4: Batch Encoding")
    print("=" * 60)
    many_texts = [f"This is sentence number {i}" for i in range(100)]
    batch_embeddings = batch_encode(many_texts, batch_size=32, is_query=False)
    print(f"Encoded {len(many_texts)} texts")
    print(f"Embeddings shape: {len(batch_embeddings)} x {len(batch_embeddings[0])}")