"""
Query Rewriter — Advanced RAG Component
========================================
Rewrites user queries into better search terms using Mistral locally.
Three strategies: simple rewrite, multi-query, and HyDE.
"""

from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

llm = OllamaLLM(model="mistral")

# ── Strategy 1: Simple rewrite ──────────────────────────────
REWRITE_PROMPT = ChatPromptTemplate.from_template("""
You are an expert at converting user questions into better search queries
for a financial document database containing Apple quarterly earnings reports.

Rewrite the following question into a precise search query that uses the
exact terminology found in Apple SEC press releases.

Apple press releases use phrases like:
- "quarterly revenue of $X billion"
- "September quarter", "December quarter", "March quarter", "June quarter"  
- "fiscal 2024", "fiscal 2025" (not Q4 FY2024)
- "Services", "iPhone", "Mac", "iPad", "Wearables"
- "year-over-year", "diluted earnings per share"

Original question: {question}

Return ONLY the rewritten search query. No explanation. No preamble.
""")

# ── Strategy 2: Multi-query ──────────────────────────────────
MULTI_QUERY_PROMPT = ChatPromptTemplate.from_template("""
You are an expert at generating multiple search query variations for a
financial document database containing Apple quarterly earnings reports.

Generate exactly 3 different phrasings of the following question.
Each phrasing should use different words but mean the same thing.
Use terminology from Apple SEC press releases.

Original question: {question}

Return ONLY 3 queries, one per line, numbered 1. 2. 3.
No explanation. No preamble.
""")

# ── Strategy 3: HyDE ────────────────────────────────────────
HYDE_PROMPT = ChatPromptTemplate.from_template("""
You are writing a passage that would appear in an Apple quarterly earnings
press release from SEC EDGAR.

Write a short 2-3 sentence passage that would answer this question,
written in the style of an Apple earnings press release.

Question: {question}

Return ONLY the passage. No explanation. No preamble.
Write as if you are Apple reporting actual results.
""")


def simple_rewrite(question: str) -> str:
    """Rewrite query once into better search terms."""
    chain = REWRITE_PROMPT | llm
    result = chain.invoke({"question": question})
    return result.strip()


def multi_query(question: str) -> list[str]:
    """Generate 3 different phrasings of the question."""
    chain = MULTI_QUERY_PROMPT | llm
    result = chain.invoke({"question": question})
    
    queries = []
    for line in result.strip().split("\n"):
        line = line.strip()
        if line and line[0].isdigit():
            # Remove leading "1. " etc
            query = line[2:].strip() if len(line) > 2 else line
            queries.append(query)
    
    # Always include original as fallback
    if not queries:
        queries = [question]
    queries.append(question)
    return queries


def hyde_query(question: str) -> str:
    """Generate a hypothetical answer and use it as search query."""
    chain = HYDE_PROMPT | llm
    result = chain.invoke({"question": question})
    return result.strip()


if __name__ == "__main__":
    # Quick test
    test_q = "What was Apple Q4 FY2024 revenue?"
    print("Original:", test_q)
    print("\nSimple rewrite:", simple_rewrite(test_q))
    print("\nMulti-query:", multi_query(test_q))
    print("\nHyDE:", hyde_query(test_q))