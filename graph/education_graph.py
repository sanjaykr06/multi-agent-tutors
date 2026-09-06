"""
Education Graph – LangGraph multi-agent state machine.

Flow:
  START → supervisor → [curriculum | tutor | quiz | evaluator | research] → END

The state tracks full conversation history and metadata so every agent
has the context it needs.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from agents.curriculum_agent import CurriculumAgent
from agents.evaluator_agent import EvaluatorAgent
from agents.quiz_agent import QuizAgent
from agents.research_agent import ResearchAgent
from agents.supervisor_agent import SupervisorAgent
from agents.tutor_agent import TutorAgent
from rag.advanced_retriever import AdvancedRetriever
from rag.vector_store import HybridVectorStore


# ---------------------------------------------------------------------------
# State definition
# ---------------------------------------------------------------------------

class EducationState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    current_agent: str
    subject: str
    student_level: str
    last_response: str
    quiz_data: dict[str, Any]
    metadata: dict[str, Any]


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

class EducationGraph:
    """LangGraph-powered multi-agent education orchestrator."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        self.llm = ChatAnthropic(
            model=model,
            temperature=0.7,
            max_tokens=2048,
            anthropic_api_key=api_key,
        )

        # Initialise RAG components
        self.vector_store = HybridVectorStore(persist_dir="vector_db")
        self.retriever = AdvancedRetriever(self.vector_store, self.llm)

        # Initialise agents
        self.supervisor = SupervisorAgent(self.llm)
        self.curriculum = CurriculumAgent(self.llm)
        self.tutor = TutorAgent(self.llm)
        self.quiz = QuizAgent(self.llm)
        self.evaluator = EvaluatorAgent(self.llm)
        self.research = ResearchAgent(self.llm, self.retriever)

        self.graph = self._build_graph()

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> Any:
        builder = StateGraph(EducationState)

        # Register nodes
        builder.add_node("supervisor", self._supervisor_node)
        builder.add_node("curriculum", self._curriculum_node)
        builder.add_node("tutor", self._tutor_node)
        builder.add_node("quiz", self._quiz_node)
        builder.add_node("evaluator", self._evaluator_node)
        builder.add_node("research", self._research_node)

        # Edges
        builder.add_edge(START, "supervisor")
        builder.add_conditional_edges(
            "supervisor",
            self._route_to_agent,
            {
                "curriculum": "curriculum",
                "tutor": "tutor",
                "quiz": "quiz",
                "evaluator": "evaluator",
                "research": "research",
            },
        )
        for node in ["curriculum", "tutor", "quiz", "evaluator", "research"]:
            builder.add_edge(node, END)

        return builder.compile()

    # ------------------------------------------------------------------
    # Node implementations
    # ------------------------------------------------------------------

    def _supervisor_node(self, state: EducationState) -> dict:
        last_msg = state["messages"][-1]
        query = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        agent = self.supervisor.route(query)
        return {"current_agent": agent, "metadata": {**state.get("metadata", {}), "routed_to": agent}}

    def _route_to_agent(self, state: EducationState) -> str:
        return state.get("current_agent", "tutor")

    def _curriculum_node(self, state: EducationState) -> dict:
        last_msg = state["messages"][-1]
        query = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        history = list(state["messages"][:-1])
        response = self.curriculum.handle(query, history)
        return {
            "messages": [AIMessage(content=response, name="curriculum")],
            "last_response": response,
        }

    def _tutor_node(self, state: EducationState) -> dict:
        last_msg = state["messages"][-1]
        query = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        history = list(state["messages"][:-1])
        response = self.tutor.handle(query, history)
        return {
            "messages": [AIMessage(content=response, name="tutor")],
            "last_response": response,
        }

    def _quiz_node(self, state: EducationState) -> dict:
        last_msg = state["messages"][-1]
        query = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        history = list(state["messages"][:-1])
        response = self.quiz.handle(query, history)
        return {
            "messages": [AIMessage(content=response, name="quiz")],
            "last_response": response,
        }

    def _evaluator_node(self, state: EducationState) -> dict:
        last_msg = state["messages"][-1]
        query = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        history = list(state["messages"][:-1])
        response = self.evaluator.handle(query, history)
        return {
            "messages": [AIMessage(content=response, name="evaluator")],
            "last_response": response,
        }

    def _research_node(self, state: EducationState) -> dict:
        last_msg = state["messages"][-1]
        query = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
        history = list(state["messages"][:-1])
        response = self.research.handle(query, history)
        return {
            "messages": [AIMessage(content=response, name="research")],
            "last_response": response,
        }

    # ------------------------------------------------------------------
    # Public run interface
    # ------------------------------------------------------------------

    def run(
        self,
        user_message: str,
        history: list[BaseMessage] | None = None,
        subject: str = "",
        student_level: str = "intermediate",
    ) -> dict[str, Any]:
        """
        Execute one turn of the education graph.
        Returns {"response": str, "agent": str}.
        """
        messages = list(history or [])
        messages.append(HumanMessage(content=user_message))

        initial_state: EducationState = {
            "messages": messages,
            "current_agent": "tutor",
            "subject": subject,
            "student_level": student_level,
            "last_response": "",
            "quiz_data": {},
            "metadata": {},
        }

        final_state = self.graph.invoke(initial_state)

        return {
            "response": final_state["last_response"],
            "agent": final_state.get("current_agent", "tutor"),
            "messages": final_state["messages"],
            "metadata": final_state.get("metadata", {}),
        }

    # ------------------------------------------------------------------
    # RAG management
    # ------------------------------------------------------------------

    def initialise_rag(self, sample_docs_dir: str = "sample_docs") -> bool:
        """Load or build the vector index. Returns True if ready."""
        try:
            # Try loading persisted index first
            if self.vector_store.load():
                return True

            # Build from sample docs directory or built-in content
            from rag.document_processor import (
                chunk_documents,
                create_sample_documents,
                load_documents_from_directory,
            )

            docs = load_documents_from_directory(sample_docs_dir)
            if not docs:
                print("[EducationGraph] No user docs found – using built-in sample content.")
                docs = create_sample_documents()

            if docs:
                chunks = chunk_documents(docs)
                self.vector_store.build(chunks)
                return True

            return False
        except Exception as exc:
            print(f"[EducationGraph] RAG initialisation failed: {exc}")
            return False

    def add_documents_to_rag(self, file_paths: list[str]) -> int:
        """Add uploaded files to the RAG index. Returns count of new chunks."""
        from rag.document_processor import chunk_documents, load_documents_from_files

        docs = load_documents_from_files(file_paths)
        if not docs:
            return 0
        chunks = chunk_documents(docs)
        self.vector_store.add_documents(chunks)
        return len(chunks)
