"""
Advanced Retriever – multi-query expansion + hybrid search pipeline.
"""

from __future__ import annotations

from typing import List

from langchain_core.documents import Document
from langchain_core.prompts import PromptTemplate
from langchain_anthropic import ChatAnthropic

from rag.vector_store import HybridVectorStore

# ---------------------------------------------------------------------------
# Multi-query prompt
# ---------------------------------------------------------------------------
MULTI_QUERY_PROMPT = PromptTemplate(
    input_variables=["question"],
    template="""You are an AI assistant helping to improve document retrieval.
Generate 3 different search query variations for the question below.
Return ONLY the queries, one per line, no numbering or extra text.

Original question: {question}

Query variations:""",
)


class AdvancedRetriever:
    """
    Three-stage retrieval pipeline:
    1. Multi-Query – generate N query variants to broaden recall.
    2. Hybrid Search – FAISS dense + BM25 sparse RRF fusion.
    3. Deduplication and top-k selection.
    """

    def __init__(self, vector_store: HybridVectorStore, llm: ChatAnthropic):
        self.vector_store = vector_store
        self.llm = llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def retrieve(self, query: str, k: int = 6) -> List[Document]:
        """Full pipeline: multi-query → hybrid search → dedup."""
        if not self.vector_store.is_ready:
            return []

        # Stage 1 – generate query variants
        queries = self._generate_query_variants(query)

        # Stage 2 – hybrid search for each variant + original
        all_docs: List[Document] = []
        for q in queries:
            docs = self.vector_store.hybrid_search(q, k=4)
            all_docs.extend(docs)

        # Also search the original with higher k
        all_docs.extend(self.vector_store.hybrid_search(query, k=6))

        # Stage 3 – deduplicate
        seen: set[str] = set()
        unique_docs: List[Document] = []
        for doc in all_docs:
            key = doc.page_content[:250]
            if key not in seen:
                seen.add(key)
                unique_docs.append(doc)

        return unique_docs[:k]

    def simple_retrieve(self, query: str, k: int = 4) -> List[Document]:
        """Fast single-pass hybrid retrieval."""
        return self.vector_store.hybrid_search(query, k=k)

    def format_context(self, docs: List[Document]) -> str:
        """Format retrieved docs into a readable context string."""
        if not docs:
            return "No relevant context found in the knowledge base."
        parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "knowledge base")
            parts.append(f"[Context {i} – {source}]\n{doc.page_content}")
        return "\n\n---\n\n".join(parts)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_query_variants(self, query: str) -> List[str]:
        """Use the LLM to generate 3 alternative phrasings of the query."""
        try:
            chain = MULTI_QUERY_PROMPT | self.llm
            response = chain.invoke({"question": query})
            content = response.content if hasattr(response, "content") else str(response)
            variants = [line.strip() for line in content.strip().split("\n") if line.strip()]
            return [query] + variants[:3]
        except Exception as exc:
            print(f"[AdvancedRetriever] Query expansion failed: {exc}")
            return [query]

