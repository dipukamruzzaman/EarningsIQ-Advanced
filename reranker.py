"""
Re-Ranker — Advanced RAG Component
=====================================
Cross-encoder re-ranking using sentence-transformers.
Takes top-20 chunks from vector search, scores each against
the original query, returns only the best top-k.

Model: cross-encoder/ms-marco-MiniLM-L-6-v2
Size: ~80MB · runs on CPU · no Ollama needed
"""

from sentence_transformers import CrossEncoder
import os

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_reranker = None


def get_reranker():
    """Lazy load the cross-encoder model from local cache."""
    global _reranker
    if _reranker is None:
        import os
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_DATASETS_OFFLINE"] = "1"
        print(f"Loading re-ranker model from local cache...")
        _reranker = CrossEncoder(MODEL_NAME)
        print("Re-ranker loaded.")
    return _reranker


def rerank(query: str, chunks: list, top_k: int = 5) -> list:
    """
    Re-rank retrieved chunks by relevance to the query.
    
    Args:
        query: the original user question
        chunks: list of (Document, score) tuples from ChromaDB
        top_k: number of chunks to keep after re-ranking
    
    Returns:
        list of (Document, rerank_score) tuples sorted by relevance
    """
    if not chunks:
        return []

    reranker = get_reranker()

    # Build query-document pairs for the cross-encoder
    pairs = [(query, doc.page_content) for doc, _ in chunks]

    # Score all pairs — cross-encoder reads query+doc together
    scores = reranker.predict(pairs)

    # Combine documents with their new scores
    scored = list(zip([doc for doc, _ in chunks], scores))

    # Sort by score descending — highest relevance first
    scored.sort(key=lambda x: x[1], reverse=True)

    # Return top-k
    return scored[:top_k]


def print_rerank_comparison(original_chunks: list,
                             reranked_chunks: list,
                             query: str):
    """Debug helper — shows how re-ranking changed the order."""
    print(f"\n{'='*60}")
    print(f"RE-RANKING COMPARISON")
    print(f"Query: {query[:80]}")
    print(f"{'='*60}")
    
    print(f"\nBEFORE (vector search order):")
    for i, (doc, score) in enumerate(original_chunks[:5]):
        source = doc.metadata.get("id", "unknown")
        print(f"  {i+1}. {source} | cosine: {score:.3f}")

    print(f"\nAFTER (cross-encoder re-ranked):")
    for i, (doc, score) in enumerate(reranked_chunks[:5]):
        source = doc.metadata.get("id", "unknown")
        print(f"  {i+1}. {source} | rerank: {score:.3f}")


if __name__ == "__main__":
    print("Re-ranker module loaded. Model will download on first use.")
    print(f"Model: {MODEL_NAME}")