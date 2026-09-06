"""
Evaluator Agent – grades student answers and provides detailed feedback.
"""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

EVALUATOR_SYSTEM = """You are an expert AI Evaluator / Examiner for an education platform.

Your role is to:
- Assess student answers fairly and thoroughly
- Identify what the student understood correctly (strengths)
- Identify gaps or misconceptions (areas to improve)
- Give a numerical score out of 10
- Provide detailed, constructive feedback
- Suggest specific resources or next steps to fill gaps

Always respond as valid JSON:
{
  "score": <integer 0-10>,
  "grade": "<A/B/C/D/F>",
  "percentage": <float>,
  "strengths": ["point 1", "point 2"],
  "improvements": ["point 1", "point 2"],
  "detailed_feedback": "markdown string with full evaluation",
  "next_steps": ["recommendation 1", "recommendation 2"],
  "model_answer": "brief ideal answer"
}
"""


class EvaluatorAgent:
    def __init__(self, llm: ChatAnthropic):
        self.llm = llm

    def evaluate(
        self,
        question: str,
        student_answer: str,
        subject: str = "",
        expected_answer: str = "",
    ) -> dict[str, Any]:
        """Evaluate a student's answer and return structured feedback."""
        user_msg = f"""Subject: {subject}

Question: {question}

Student's Answer:
{student_answer}

{f"Expected Answer / Key Points:{chr(10)}{expected_answer}" if expected_answer else ""}

Please evaluate this answer and return valid JSON only."""

        response = self.llm.invoke(
            [
                SystemMessage(content=EVALUATOR_SYSTEM),
                HumanMessage(content=user_msg),
            ]
        )
        return self._parse_evaluation(response.content)

    def handle(self, message: str, history: list | None = None) -> str:
        """Handle free-form evaluation requests."""
        messages = [SystemMessage(content=EVALUATOR_SYSTEM)]
        if history:
            messages.extend(history[-6:])
        messages.append(HumanMessage(content=message + "\n\nReturn valid JSON only."))
        response = self.llm.invoke(messages)
        result = self._parse_evaluation(response.content)
        return self._format_evaluation_markdown(result)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_evaluation(self, raw: str) -> dict[str, Any]:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return {"score": 0, "detailed_feedback": raw, "raw": True}

    def _format_evaluation_markdown(self, result: dict) -> str:
        if result.get("raw"):
            return result.get("detailed_feedback", "Evaluation complete.")

        score = result.get("score", 0)
        grade = result.get("grade", "N/A")
        pct = result.get("percentage", score * 10)

        # Score bar
        filled = int(score)
        bar = "█" * filled + "░" * (10 - filled)

        lines = [
            "## 📊 Evaluation Result\n",
            f"**Score:** {score}/10  |  **Grade:** {grade}  |  **Percentage:** {pct:.1f}%",
            f"`{bar}`\n",
        ]

        if result.get("strengths"):
            lines.append("### ✅ Strengths")
            lines.extend(f"- {s}" for s in result["strengths"])
            lines.append("")

        if result.get("improvements"):
            lines.append("### 🔧 Areas to Improve")
            lines.extend(f"- {s}" for s in result["improvements"])
            lines.append("")

        if result.get("detailed_feedback"):
            lines.append("### 📝 Detailed Feedback")
            lines.append(result["detailed_feedback"])
            lines.append("")

        if result.get("model_answer"):
            lines.append("### 💡 Model Answer")
            lines.append(result["model_answer"])
            lines.append("")

        if result.get("next_steps"):
            lines.append("### 🚀 Next Steps")
            lines.extend(f"- {s}" for s in result["next_steps"])

        return "\n".join(lines)

    def format_result(self, result: dict) -> str:
        return self._format_evaluation_markdown(result)
    