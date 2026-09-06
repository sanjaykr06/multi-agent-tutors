"""
Research Agent – RAG-powered deep knowledge retrieval agent.
Answers questions grounded in the uploaded educational document corpus.
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from rag.advanced_retriever import AdvancedRetriever

RESEARCH_SYSTEM = """You are an expert Research Assistant for an AI Education Platform.
You answer student questions strictly grounded in the provided source documents.

Rules:
- Answer ONLY from the provided context. If the context doesn't contain the answer, say so clearly.
- Quote or reference specific sections when helpful.
- Explain concepts in clear, educational language.
- Structure your answer with headers and bullet points when helpful.
- Always end with 1–2 follow-up questions to deepen understanding.

If the context is insufficient, say: "I couldn't find detailed information on this in the current
knowledge base. Here's what I know from general knowledge:" and then answer carefully.
"""


class ResearchAgent:
    def __init__(self, llm: ChatAnthropic, retriever: AdvancedRetriever):
        self.llm = llm
        self.retriever = retriever

    def research(self, question: str, history: list | None = None) -> str:
        """Answer a question using the RAG pipeline."""
        # Retrieve relevant context
        docs = self.retriever.retrieve(question, k=5)
        context = self.retriever.format_context(docs)

        system_with_context = f"""{RESEARCH_SYSTEM}

=== KNOWLEDGE BASE CONTEXT ===
{context}
=== END CONTEXT ===
"""
        messages = [SystemMessage(content=system_with_context)]
        if history:
            messages.extend(history[-6:])
        messages.append(HumanMessage(content=question))

        response = self.llm.invoke(messages)
        return response.content

    def handle(self, message: str, history: list | None = None) -> str:
        return self.research(message, history)

    def get_sources(self, question: str) -> list[dict]:
        """Return the source documents used for a query (for citation display)."""
        docs = self.retriever.simple_retrieve(question, k=4)
        sources = []
        for doc in docs:
            sources.append(
                {
                    "source": doc.metadata.get("source", "unknown"),
                    "subject": doc.metadata.get("subject", ""),
                    "preview": doc.page_content[:200] + "…",
                }
            )
        return sources
