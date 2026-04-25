"""
Advanced Query Pipeline
========================
Combines query rewriting + re-ranking for dramatically better retrieval.

Usage:
    python advanced_query.py "What was Apple revenue in Q4 FY2024?"
    python advanced_query.py "Q4 FY2024 revenue" --strategy multi
    python advanced_query.py "iPhone revenue 2022" --strategy hyde
"""

import argparse
import os
import time
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from get_embedding_function import get_embedding_function
from query_rewriter import simple_rewrite, multi_query, hyde_query
from reranker import rerank, print_rerank_comparison

CHROMA_PATH = "chroma"

PROMPT_TEMPLATE = """
You are a financial analyst assistant. Answer the question using ONLY the context below.
Be direct and confident. If the answer contains a specific number, state it clearly first.
Do not say the context "does not specify" if the number appears anywhere in the context.

Context:
{context}

---

Question: {question}

Answer directly with the specific figure. One or two sentences maximum.
"""


def advanced_rag(question: str,
                 strategy: str = "rewrite",
                 retrieval_k: int = 20,
                 final_k: int = 5,
                 verbose: bool = False) -> dict:
    """
    Full advanced RAG pipeline.
    
    Args:
        question: user's original question
        strategy: "rewrite", "multi", or "hyde"
        retrieval_k: how many chunks to retrieve before re-ranking
        final_k: how many chunks to keep after re-ranking
        verbose: print debug information
    
    Returns:
        dict with response, sources, rewrite, timing info
    """
    start = time.time()
    results = {}

    # ── Step 1: Query Rewriting ──────────────────────────────
    t1 = time.time()
    
    if strategy == "rewrite":
        search_query = simple_rewrite(question)
        search_queries = [search_query]
        results["rewrite_strategy"] = "simple"
        results["rewritten_query"] = search_query

    elif strategy == "multi":
        search_queries = multi_query(question)
        results["rewrite_strategy"] = "multi-query"
        results["rewritten_queries"] = search_queries

    elif strategy == "hyde":
        search_query = hyde_query(question)
        search_queries = [search_query]
        results["rewrite_strategy"] = "HyDE"
        results["hypothetical_doc"] = search_query

    else:
        search_queries = [question]
        results["rewrite_strategy"] = "none"

    results["rewrite_time"] = round(time.time() - t1, 1)

    if verbose:
        print(f"\n[Step 1] Query rewriting ({strategy})")
        for q in search_queries:
            print(f"  → {q[:100]}")

    # ── Step 2: Vector Retrieval ─────────────────────────────
    t2 = time.time()
    embedding_function = get_embedding_function()
    db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embedding_function
    )

    # Retrieve chunks for each query and merge
    all_chunks = []
    seen_ids = set()

    for query in search_queries:
        retrieved = db.similarity_search_with_score(query, k=retrieval_k)
        for doc, score in retrieved:
            doc_id = doc.metadata.get("id", doc.page_content[:50])
            if doc_id not in seen_ids:
                all_chunks.append((doc, score))
                seen_ids.add(doc_id)

    results["retrieval_count"] = len(all_chunks)
    results["retrieval_time"] = round(time.time() - t2, 1)

    if verbose:
        print(f"\n[Step 2] Retrieved {len(all_chunks)} unique chunks")

    # ── Step 3: Re-ranking ───────────────────────────────────
    t3 = time.time()
    reranked = rerank(question, all_chunks, top_k=final_k)
    results["rerank_time"] = round(time.time() - t3, 1)

    if verbose:
        print_rerank_comparison(all_chunks[:final_k], reranked, question)

    # ── Step 4: Generate Answer ──────────────────────────────
    t4 = time.time()
    context = "\n\n---\n\n".join([doc.page_content for doc, _ in reranked])

    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context, question=question)

    model = OllamaLLM(model="mistral")
    response = model.invoke(prompt)
    results["generation_time"] = round(time.time() - t4, 1)

    # ── Step 5: Package results ──────────────────────────────
    results["response"] = response
    results["sources"] = [
        doc.metadata.get("id", doc.metadata.get("source", "unknown"))
        for doc, _ in reranked
    ]
    results["rerank_scores"] = [round(float(score), 3) for _, score in reranked]
    results["total_time"] = round(time.time() - start, 1)

    return results


def main():
    parser = argparse.ArgumentParser(description="Advanced RAG query")
    parser.add_argument("query_text", type=str, help="Your question")
    parser.add_argument("--strategy", type=str, default="rewrite",
                        choices=["rewrite", "multi", "hyde", "none"],
                        help="Query rewriting strategy")
    parser.add_argument("--k", type=int, default=20,
                        help="Chunks to retrieve before re-ranking")
    parser.add_argument("--final-k", type=int, default=5,
                        help="Chunks to keep after re-ranking")
    parser.add_argument("--verbose", action="store_true",
                        help="Show debug information")
    args = parser.parse_args()

    print(f"\nQuestion: {args.query_text}")
    print(f"Strategy: {args.strategy}")
    print("Processing...\n")

    result = advanced_rag(
        question=args.query_text,
        strategy=args.strategy,
        retrieval_k=args.k,
        final_k=args.final_k,
        verbose=args.verbose
    )

    print(f"Response: {result['response']}")
    print(f"\nSources: {result['sources']}")
    print(f"Re-rank scores: {result['rerank_scores']}")
    print(f"\nTiming breakdown:")
    print(f"  Query rewrite : {result['rewrite_time']}s")
    print(f"  Retrieval     : {result['retrieval_time']}s")
    print(f"  Re-ranking    : {result['rerank_time']}s")
    print(f"  Generation    : {result['generation_time']}s")
    print(f"  Total         : {result['total_time']}s")

    if "rewritten_query" in result:
        print(f"\nRewritten query: {result['rewritten_query']}")
    if "rewritten_queries" in result:
        print(f"\nMulti-queries:")
        for q in result["rewritten_queries"]:
            print(f"  → {q}")


if __name__ == "__main__":
    main()