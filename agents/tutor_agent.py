"""
Tutor Agent – Socratic step-by-step concept explainer.
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

TUTOR_SYSTEM = """You are an expert AI Tutor on an education platform. You excel at explaining
complex concepts clearly and engagingly to students of all levels.

Your teaching style:
- Use the Socratic method: ask guiding questions to help students discover answers
- Break complex concepts into small, digestible steps
- Use analogies, real-world examples, and visuals (described in text)
- Check understanding with a quick comprehension question at the end
- Adapt your language to the student's apparent level
- Use markdown formatting: headers, bullet points, code blocks where relevant
- For math/science, show step-by-step working
- Always encourage curiosity

Never just give raw answers — guide the student through the reasoning process.
"""


class TutorAgent:
    def __init__(self, llm: ChatAnthropic):
        self.llm = llm

    def explain(
        self,
        concept: str,
        subject: str = "",
        level: str = "intermediate",
        history: list | None = None,
    ) -> str:
        """Explain a concept with step-by-step guidance."""
        context_prefix = f"Subject: {subject}\nStudent Level: {level}\n\n" if subject else ""
        user_msg = f"{context_prefix}Please explain: {concept}"

        messages = [SystemMessage(content=TUTOR_SYSTEM)]
        if history:
            messages.extend(history[-8:])
        messages.append(HumanMessage(content=user_msg))

        response = self.llm.invoke(messages)
        return response.content

    def handle(self, message: str, history: list | None = None) -> str:
        """Handle any tutoring conversation turn."""
        messages = [SystemMessage(content=TUTOR_SYSTEM)]
        if history:
            messages.extend(history[-8:])
        messages.append(HumanMessage(content=message))
        response = self.llm.invoke(messages)
        return response.content
