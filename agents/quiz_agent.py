"""
Quiz Agent – generates adaptive quizzes (MCQ, short-answer, coding).
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

QUIZ_SYSTEM = """You are an expert Quiz Generator for an AI Education Platform.

You create high-quality, pedagogically sound quizzes. For every quiz:
- Vary difficulty (30% easy, 50% medium, 20% hard)
- Test conceptual understanding, not just memorisation
- For MCQs: provide 4 options with ONLY one correct answer
- Include brief explanation for the correct answer

IMPORTANT: Always return your response as valid JSON matching this exact format:
{
  "quiz_title": "string",
  "subject": "string",
  "total_marks": number,
  "questions": [
    {
      "id": 1,
      "type": "mcq",
      "question": "string",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct_answer": "A",
      "explanation": "string",
      "marks": number,
      "difficulty": "easy|medium|hard"
    }
  ]
}

For short-answer questions omit the "options" field and set "correct_answer" to the expected key points.
"""


class QuizAgent:
    def __init__(self, llm: ChatAnthropic):
        self.llm = llm

    def generate_quiz(
        self,
        topic: str,
        num_questions: int = 5,
        quiz_type: str = "mixed",
        difficulty: str = "medium",
        subject: str = "",
    ) -> dict[str, Any]:
        """Generate a structured quiz on the given topic."""
        user_msg = f"""Create a {quiz_type} quiz on: {topic}
Subject area: {subject or topic}
Number of questions: {num_questions}
Overall difficulty: {difficulty}
Question types: {"MCQ and short-answer mix" if quiz_type == "mixed" else quiz_type}

Return valid JSON only."""

        response = self.llm.invoke(
            [
                SystemMessage(content=QUIZ_SYSTEM),
                HumanMessage(content=user_msg),
            ]
        )
        return self._parse_quiz(response.content)

    def handle(self, message: str, history: list | None = None) -> str:
        """Handle a free-form quiz request, return formatted quiz string."""
        messages = [SystemMessage(content=QUIZ_SYSTEM)]
        if history:
            messages.extend(history[-4:])
        messages.append(HumanMessage(content=message + "\n\nReturn valid JSON only."))
        response = self.llm.invoke(messages)
        quiz = self._parse_quiz(response.content)
        return self._format_quiz_markdown(quiz)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_quiz(self, raw: str) -> dict[str, Any]:
        """Extract JSON from the model response."""
        try:
            # Try direct parse first
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON block
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        # Fallback
        return {"quiz_title": "Quiz", "questions": [], "raw": raw}

    def _format_quiz_markdown(self, quiz: dict) -> str:
        if "raw" in quiz:
            return quiz["raw"]

        lines = [f"## 📝 {quiz.get('quiz_title', 'Quiz')}\n"]
        lines.append(f"**Subject:** {quiz.get('subject', '')}")
        lines.append(f"**Total Marks:** {quiz.get('total_marks', len(quiz.get('questions', [])))}\n")

        for q in quiz.get("questions", []):
            diff_icon = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(
                q.get("difficulty", "medium"), "🟡"
            )
            lines.append(
                f"**Q{q['id']}** {diff_icon} ({q.get('marks', 1)} mark) – "
                f"*{q.get('difficulty', 'medium')}*"
            )
            lines.append(f"{q['question']}\n")
            for opt in q.get("options", []):
                lines.append(f"  - {opt}")
            lines.append("")

        return "\n".join(lines)

    def format_quiz_for_display(self, quiz: dict) -> str:
        return self._format_quiz_markdown(quiz)

    def reveal_answers(self, quiz: dict) -> str:
        """Format quiz with correct answers and explanations revealed."""
        lines = [f"## ✅ Answer Key: {quiz.get('quiz_title', 'Quiz')}\n"]
        for q in quiz.get("questions", []):
            lines.append(f"**Q{q['id']}.** {q['question']}")
            lines.append(f"✅ **Correct Answer:** {q.get('correct_answer', 'N/A')}")
            lines.append(f"💡 **Explanation:** {q.get('explanation', '')}\n")
        return "\n".join(lines)
