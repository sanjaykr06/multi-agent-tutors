
"""Shared utilities."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_api_key() -> str:
    """Load ANTHROPIC_API_KEY from .env or environment."""
    # Walk up to find a .env file
    search = Path(__file__).parent
    for _ in range(5):
        env_file = search / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            break
        search = search.parent
    else:
        load_dotenv()

    key = os.getenv("ANTHROPIC_API_KEY", "")
    return key


def load_config() -> dict:
    """Load config.json from the parent directory."""
    import json

    config_paths = [
        Path(__file__).parent / "config.json",
        Path(__file__).parent.parent / "config.json",
    ]
    for p in config_paths:
        if p.exists():
            with open(p) as f:
                return json.load(f)
    return {}


def format_agent_badge(agent_name: str) -> str:
    """Return an emoji badge for a given agent name."""
    badges = {
        "supervisor": "🎯 Supervisor",
        "curriculum": "📚 Curriculum Designer",
        "tutor": "🧑‍🏫 AI Tutor",
        "quiz": "📝 Quiz Master",
        "evaluator": "📊 Evaluator",
        "research": "🔍 Research Agent",
    }
    return badges.get(agent_name, f"🤖 {agent_name.title()}")


AGENT_DESCRIPTIONS = {
    "curriculum": "Creates personalised study plans and learning paths.",
    "tutor": "Explains concepts step-by-step using the Socratic method.",
    "quiz": "Generates adaptive quizzes to test your understanding.",
    "evaluator": "Grades your answers and gives detailed feedback.",
    "research": "Searches the knowledge base for deep, document-grounded answers.",
}
