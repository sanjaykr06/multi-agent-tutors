"""
Curriculum Agent – builds personalised, structured learning paths.
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

CURRICULUM_SYSTEM = """You are an expert Curriculum Designer for an AI Education Platform.

Your responsibilities:
- Create detailed, structured learning paths for any subject or topic
- Personalise the plan based on the student's current level (beginner/intermediate/advanced)
- Break the learning journey into weekly modules with clear goals
- Suggest resources, exercises, and milestones
- Estimate time commitments realistically

Format your response as a well-structured learning plan with:
1. **Overview** – what the student will achieve
2. **Prerequisites** – what they should already know
3. **Week-by-Week Plan** – topics, goals, and activities for each week
4. **Resources** – books, online courses, practice sites
5. **Milestones** – how to know they've mastered each phase

Be encouraging, specific, and actionable.
"""


class CurriculumAgent:
    def __init__(self, llm: ChatAnthropic):
        self.llm = llm

    def create_learning_path(
        self, subject: str, student_level: str = "beginner", goals: str = ""
    ) -> str:
        """Generate a full personalised learning plan."""
        user_msg = f"""Subject: {subject}
Student Level: {student_level}
Student Goals: {goals if goals else 'Master the fundamentals and advance to intermediate level'}

Please create a comprehensive, personalised learning path."""

        response = self.llm.invoke(
            [
                SystemMessage(content=CURRICULUM_SYSTEM),
                HumanMessage(content=user_msg),
            ]
        )
        return response.content

    def handle(self, message: str, history: list | None = None) -> str:
        """Handle a free-form curriculum request."""
        messages = [SystemMessage(content=CURRICULUM_SYSTEM)]
        if history:
            messages.extend(history[-6:])  # last 3 turns
        messages.append(HumanMessage(content=message))
        response = self.llm.invoke(messages)
        return response.content

