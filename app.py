"""
🎓 Multi-Agent AI Education Platform
=====================================
Streamlit UI — entry point: `streamlit run app.py`
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

# Ensure project root is on sys.path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from utils.helpers import AGENT_DESCRIPTIONS, format_agent_badge, load_api_key

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="🎓 Multi-Agent AI Education Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
    .main-title { font-size: 2.4rem; font-weight: 800; color: #1a1a2e; }
    .sub-title  { font-size: 1.1rem; color: #666; margin-bottom: 1rem; }
    .agent-badge {
        display: inline-block; padding: 4px 12px; border-radius: 20px;
        font-weight: 600; font-size: 0.85rem; margin-bottom: 8px;
        background: linear-gradient(135deg, #667eea, #764ba2); color: white;
    }
    .stChatMessage { border-radius: 12px; }
    .metric-card {
        background: #f8f9fa; border-radius: 10px; padding: 12px;
        border-left: 4px solid #667eea; margin-bottom: 8px;
    }
    .rag-source {
        background: #e8f4fd; border-radius: 8px; padding: 8px;
        border-left: 3px solid #3498db; font-size: 0.85rem; margin: 4px 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def init_session():
    defaults = {
        "messages": [],          # List of {"role": "user"|"assistant", "content": str, "agent": str}
        "graph": None,
        "rag_ready": False,
        "api_key": "",
        "subject": "General",
        "level": "Intermediate",
        "quiz_state": None,      # Current quiz dict
        "eval_mode": False,
        "doc_count": 0,
        "agent_stats": {"tutor": 0, "quiz": 0, "curriculum": 0, "evaluator": 0, "research": 0},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # API key is loaded only from the environment / .env file — never surfaced in the UI.
    if not st.session_state.api_key:
        st.session_state.api_key = load_api_key()


init_session()


# ---------------------------------------------------------------------------
# Backend initialisation
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="🚀 Initialising AI agents …")
def get_graph(api_key: str, model: str):
    """Initialise the LangGraph education graph (cached per API key + model)."""
    from graph.education_graph import EducationGraph

    graph = EducationGraph(api_key=api_key, model=model)
    return graph


def ensure_graph():
    """Make sure the graph is initialised and stored in session state."""
    key = st.session_state.api_key
    if not key:
        return False
    if st.session_state.graph is None:
        cfg = _load_config()
        model = cfg.get("anthropicai", {}).get("model", "claude-sonnet-4-5-20250929")
        st.session_state.graph = get_graph(key, model)
    return True


def ensure_rag():
    """Initialise RAG on first use."""
    if not st.session_state.rag_ready and st.session_state.graph:
        with st.spinner("📚 Building knowledge index …"):
            ok = st.session_state.graph.initialise_rag(
                str(ROOT / "sample_docs")
            )
            st.session_state.rag_ready = ok
    return st.session_state.rag_ready


def _load_config() -> dict:
    import json
    cfg_path = ROOT.parent / "config.json"
    if cfg_path.exists():
        with open(cfg_path) as f:
            return json.load(f)
    return {}


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar():
    with st.sidebar:
        st.markdown("## 🎓 Education Platform")
        st.markdown("*Multi-Agent AI powered by Anthropic Claude*")
        st.divider()

        if not st.session_state.api_key:
            st.error("⚠️ ANTHROPIC_API_KEY not found. Set it in your .env file and restart the app.")

        st.divider()

        # --- Student Profile ---
        st.markdown("### 👤 Student Profile")
        st.session_state.subject = st.selectbox(
            "Subject Focus",
            ["General", "Mathematics", "Physics", "Computer Science",
             "Machine Learning", "Chemistry", "Biology", "History", "Literature"],
        )
        st.session_state.level = st.selectbox(
            "Learning Level",
            ["Beginner", "Intermediate", "Advanced"],
            index=1,
        )

        st.divider()

        # --- Document Upload ---
        st.markdown("### 📤 Upload Study Materials")
        uploaded = st.file_uploader(
            "Upload PDFs or TXTs",
            type=["pdf", "txt"],
            accept_multiple_files=True,
            help="Upload your own educational documents to enhance the knowledge base",
        )
        if uploaded and st.button("📥 Index Documents", use_container_width=True):
            _handle_uploads(uploaded)

        if st.session_state.rag_ready:
            st.success("✅ Knowledge base ready")
        else:
            if st.button("🔨 Build Knowledge Base", use_container_width=True):
                ensure_graph()
                ensure_rag()

        st.divider()

        # --- Quick actions ---
        st.markdown("### ⚡ Quick Actions")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📚 Study Plan", use_container_width=True):
                _quick_action(f"Create a study plan for {st.session_state.subject}")
            if st.button("🔍 Deep Q&A", use_container_width=True):
                _quick_action(f"Tell me about key concepts in {st.session_state.subject} from the documents")
        with col2:
            if st.button("📝 Quiz Me", use_container_width=True):
                _quick_action(f"Generate a quiz on {st.session_state.subject} for {st.session_state.level} level")
            if st.button("💡 Explain", use_container_width=True):
                _quick_action(f"Explain a fundamental concept in {st.session_state.subject}")

        if st.button("🗑️ Clear Chat", use_container_width=True, type="secondary"):
            st.session_state.messages = []
            st.rerun()

        st.divider()

        # --- Agent Stats ---
        st.markdown("### 📊 Session Stats")
        stats = st.session_state.agent_stats
        total = sum(stats.values())
        if total:
            for agent, count in stats.items():
                if count > 0:
                    badge = format_agent_badge(agent)
                    st.markdown(f"**{badge}**: {count} interaction{'s' if count != 1 else ''}")
        else:
            st.caption("No interactions yet")

        # --- Agents Overview ---
        st.divider()
        st.markdown("### 🤖 Available Agents")
        for agent, desc in AGENT_DESCRIPTIONS.items():
            with st.expander(format_agent_badge(agent)):
                st.caption(desc)


def _handle_uploads(uploaded_files):
    if not ensure_graph():
        st.error("Please enter your API key first.")
        return
    ensure_rag()
    tmp_paths = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for uf in uploaded_files:
            tmp_path = os.path.join(tmpdir, uf.name)
            with open(tmp_path, "wb") as f:
                f.write(uf.getvalue())
            tmp_paths.append(tmp_path)
        count = st.session_state.graph.add_documents_to_rag(tmp_paths)
    st.session_state.rag_ready = True
    st.success(f"✅ Indexed {count} chunks from {len(uploaded_files)} file(s)!")


def _quick_action(message: str):
    st.session_state["_pending_message"] = message
    st.rerun()


# ---------------------------------------------------------------------------
# Main chat area
# ---------------------------------------------------------------------------

def render_chat():
    st.markdown(
        '<div class="main-title">🎓 Multi-Agent AI Education Platform</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-title">Ask anything • Get a study plan • Take a quiz • Evaluate your answers • Research deep topics</div>',
        unsafe_allow_html=True,
    )

    # Agent capability cards
    with st.expander("🤖 How does this work?", expanded=False):
        cols = st.columns(5)
        icons = ["📚", "🧑‍🏫", "📝", "📊", "🔍"]
        agents = ["curriculum", "tutor", "quiz", "evaluator", "research"]
        for col, icon, agent in zip(cols, icons, agents):
            with col:
                st.markdown(f"**{icon} {agent.title()}**")
                st.caption(AGENT_DESCRIPTIONS[agent])

    st.divider()

    # Chat history
    chat_container = st.container()
    with chat_container:
        if not st.session_state.messages:
            st.info(
                "👋 Welcome! I'm your AI Education Assistant.\n\n"
                "Try asking:\n"
                "- *'Create a 4-week study plan for Machine Learning'*\n"
                "- *'Explain gradient descent step by step'*\n"
                "- *'Quiz me on Python data structures'*\n"
                "- *'Evaluate my answer: [paste your answer]'*\n"
                "- *'What does the document say about neural networks?'*"
            )

        for msg in st.session_state.messages:
            role = msg["role"]
            content = msg["content"]
            agent = msg.get("agent", "")

            with st.chat_message(role, avatar="👤" if role == "user" else "🎓"):
                if role == "assistant" and agent:
                    badge = format_agent_badge(agent)
                    st.markdown(
                        f'<div class="agent-badge">{badge}</div>', unsafe_allow_html=True
                    )
                st.markdown(content)

    # Handle pending quick-action messages
    if "_pending_message" in st.session_state:
        pending = st.session_state.pop("_pending_message")
        _process_message(pending)

    # Chat input
    if prompt := st.chat_input(
        "Ask a question, request a study plan, quiz, or paste your answer for evaluation…"
    ):
        _process_message(prompt)


def _process_message(user_input: str):
    if not st.session_state.api_key:
        st.error("⚠️ ANTHROPIC_API_KEY not configured. Set it in your .env file and restart the app.")
        return

    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": user_input})

    if not ensure_graph():
        st.error("Could not initialise the AI graph. Check your API key.")
        return

    # Build LangChain message history
    lc_history = []
    for m in st.session_state.messages[:-1]:
        if m["role"] == "user":
            lc_history.append(HumanMessage(content=m["content"]))
        else:
            lc_history.append(AIMessage(content=m["content"]))

    # Ensure RAG is ready for research queries
    ensure_rag()

    with st.spinner("🤔 Thinking …"):
        try:
            result = st.session_state.graph.run(
                user_message=user_input,
                history=lc_history,
                subject=st.session_state.subject,
                student_level=st.session_state.level.lower(),
            )
            response = result["response"]
            agent_used = result.get("agent", "tutor")

            # Update stats
            if agent_used in st.session_state.agent_stats:
                st.session_state.agent_stats[agent_used] += 1

            st.session_state.messages.append(
                {"role": "assistant", "content": response, "agent": agent_used}
            )
        except Exception as exc:
            err_msg = f"❌ Error: {exc}\n\nPlease check your API key and try again."
            st.session_state.messages.append(
                {"role": "assistant", "content": err_msg, "agent": "system"}
            )

    st.rerun()


# ---------------------------------------------------------------------------
# Dedicated Quiz mode tab
# ---------------------------------------------------------------------------

def render_quiz_tab():
    st.markdown("## 📝 Interactive Quiz Mode")
    st.caption("Generate a structured quiz and answer interactively.")

    if not st.session_state.api_key:
        st.warning("ANTHROPIC_API_KEY not configured. Set it in your .env file and restart the app.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        topic = st.text_input("Quiz Topic", value=st.session_state.subject)
    with col2:
        n_q = st.slider("Number of Questions", 3, 10, 5)
    with col3:
        difficulty = st.selectbox("Difficulty", ["easy", "medium", "hard", "mixed"], index=1)

    if st.button("🎯 Generate Quiz", type="primary", use_container_width=True):
        if not ensure_graph():
            st.error("Graph not ready.")
            return
        with st.spinner("Generating quiz …"):
            quiz = st.session_state.graph.quiz.generate_quiz(
                topic=topic,
                num_questions=n_q,
                difficulty=difficulty,
                subject=st.session_state.subject,
            )
            st.session_state.quiz_state = quiz

    if st.session_state.quiz_state:
        quiz = st.session_state.quiz_state
        if "raw" in quiz:
            st.markdown(quiz.get("raw", ""))
            return

        st.markdown(f"### {quiz.get('quiz_title', 'Quiz')}")
        st.caption(
            f"Subject: {quiz.get('subject', '')} | "
            f"Total Marks: {quiz.get('total_marks', n_q)}"
        )
        st.divider()

        answers: dict[int, str] = {}
        for q in quiz.get("questions", []):
            qid = q["id"]
            diff_icon = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(
                q.get("difficulty", "medium"), "🟡"
            )
            st.markdown(f"**Q{qid}** {diff_icon} – *{q.get('difficulty', 'medium')}*")
            st.markdown(q["question"])

            if q.get("options"):
                answers[qid] = st.radio(
                    f"Q{qid}",
                    q["options"],
                    key=f"q_{qid}",
                    label_visibility="collapsed",
                )
            else:
                answers[qid] = st.text_area(
                    f"Your answer for Q{qid}",
                    key=f"q_{qid}",
                    height=80,
                )
            st.divider()

        if st.button("✅ Submit & See Answers", type="primary", use_container_width=True):
            st.markdown("## 📊 Results")
            correct = 0
            for q in quiz.get("questions", []):
                qid = q["id"]
                student_ans = answers.get(qid, "")
                expected = q.get("correct_answer", "")
                is_correct = expected.strip()[0].upper() == str(student_ans).strip()[0].upper() if student_ans and expected else False
                if is_correct:
                    correct += 1
                icon = "✅" if is_correct else "❌"
                st.markdown(f"{icon} **Q{qid}:** {q['question']}")
                st.markdown(f"   - Your answer: **{student_ans}**")
                st.markdown(f"   - Correct answer: **{expected}**")
                st.info(f"💡 {q.get('explanation', '')}")
            pct = (correct / max(len(quiz.get("questions", [1])), 1)) * 100
            st.success(f"🏆 Score: {correct}/{len(quiz.get('questions', []))} ({pct:.0f}%)")
            if pct >= 80:
                st.balloons()


# ---------------------------------------------------------------------------
# Research / RAG tab
# ---------------------------------------------------------------------------

def render_research_tab():
    st.markdown("## 🔍 Research & Deep Q&A")
    st.caption("Ask questions grounded in uploaded educational documents.")

    ensure_graph()
    ensure_rag()

    if not st.session_state.api_key:
        st.warning("ANTHROPIC_API_KEY not configured. Set it in your .env file and restart the app.")
        return

    query = st.text_area(
        "Your research question",
        placeholder="What does the document say about derivatives?\nExplain neural network backpropagation from the source material.",
        height=100,
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        show_sources = st.checkbox("Show retrieved sources", value=True)
    with col2:
        if st.button("🔍 Research", type="primary", use_container_width=True):
            if query.strip() and ensure_graph():
                with st.spinner("Searching knowledge base …"):
                    answer = st.session_state.graph.research.research(query)
                    sources = (
                        st.session_state.graph.research.get_sources(query)
                        if show_sources
                        else []
                    )

                st.markdown("### 📖 Answer")
                st.markdown(answer)

                if sources:
                    st.markdown("### 📚 Sources Retrieved")
                    for src in sources:
                        with st.expander(f"📄 {src['source']} — {src.get('subject', '')}"):
                            st.markdown(
                                f'<div class="rag-source">{src["preview"]}</div>',
                                unsafe_allow_html=True,
                            )


# ---------------------------------------------------------------------------
# Evaluator tab
# ---------------------------------------------------------------------------

def render_eval_tab():
    st.markdown("## 📊 Answer Evaluator")
    st.caption("Submit your answer and get detailed AI feedback.")

    if not st.session_state.api_key:
        st.warning("ANTHROPIC_API_KEY not configured. Set it in your .env file and restart the app.")
        return

    col1, col2 = st.columns(2)
    with col1:
        question = st.text_area("Question / Problem", height=120, placeholder="What is Newton's second law?")
        subject = st.text_input("Subject", value=st.session_state.subject)
    with col2:
        student_answer = st.text_area("Your Answer", height=120, placeholder="Paste your answer here…")
        expected = st.text_area("Expected Answer (optional)", height=80, placeholder="Leave blank for auto-evaluation")

    if st.button("📊 Evaluate My Answer", type="primary", use_container_width=True):
        if question.strip() and student_answer.strip():
            if not ensure_graph():
                st.error("Graph not ready.")
                return
            with st.spinner("Evaluating …"):
                result = st.session_state.graph.evaluator.evaluate(
                    question=question,
                    student_answer=student_answer,
                    subject=subject,
                    expected_answer=expected,
                )
                formatted = st.session_state.graph.evaluator.format_result(result)

            st.markdown(formatted)
            if result.get("score", 0) >= 8:
                st.balloons()
        else:
            st.warning("Please enter both a question and your answer.")


# ---------------------------------------------------------------------------
# App layout – tabs
# ---------------------------------------------------------------------------

def main():
    render_sidebar()

    tab1, tab2, tab3, tab4 = st.tabs(
        ["💬 Chat Tutor", "📝 Quiz Mode", "🔍 Research", "📊 Evaluator"]
    )

    with tab1:
        render_chat()
    with tab2:
        render_quiz_tab()
    with tab3:
        render_research_tab()
    with tab4:
        render_eval_tab()


if __name__ == "__main__":
    main()
