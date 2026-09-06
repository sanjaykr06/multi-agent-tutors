"""
Supervisor Agent – analyses student intent and routes to the best specialist.
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

SUPERVISOR_SYSTEM = """You are the Supervisor of an AI Education Platform.
Your job is to analyse the student's message and decide which specialist agent should handle it.

Available agents:
- "curriculum"  → student wants a study plan, learning path, or curriculum for a subject
- "tutor"        → student wants an explanation, wants to understand a concept, or asks "how/why/what"
- "quiz"         → student wants to be tested, wants practice questions, or asks for a quiz
- "evaluator"    → student submitted an answer and wants it graded/evaluated
- "research"     → student is asking a deep question that may require searching educational documents

Respond with ONLY one of these exact words: curriculum, tutor, quiz, evaluator, research
"""


class SupervisorAgent:
    def __init__(self, llm: ChatAnthropic):
        self.llm = llm

    def route(self, message: str, context: str = "") -> str:
        """Return the name of the agent that should handle this message."""
        user_content = message
        if context:
            user_content = f"Previous context: {context}\n\nStudent message: {message}"

        response = self.llm.invoke(
            [
                SystemMessage(content=SUPERVISOR_SYSTEM),
                HumanMessage(content=user_content),
            ]
        )
        decision = response.content.strip().lower()

        valid_agents = {"curriculum", "tutor", "quiz", "evaluator", "research"}
        # Fallback to tutor if the model returns unexpected text
        for agent in valid_agents:
            if agent in decision:
                return agent
        return "tutor"
