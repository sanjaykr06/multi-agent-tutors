# 🎓 Multi-Agent AI Education Platform — Technical Document

**Project:** Multi-Agent AI Tutoring System  
**Institution:** IIT Patna  
**Version:** 1.0  
**Date:** May 22, 2026  
**Entry Point:** `streamlit run app.py`

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technologies Used](#2-technologies-used)
3. [Technical Architecture](#3-technical-architecture)
4. [Business Architecture](#4-business-architecture)
5. [Module Reference](#5-module-reference)
6. [Data Flow](#6-data-flow)
7. [Configuration Reference](#7-configuration-reference)
8. [User Manual](#8-user-manual)
9. [Installation & Setup](#9-installation--setup)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Project Overview

The **Multi-Agent AI Education Platform** is an intelligent, conversational tutoring system that routes student queries to a team of specialised AI agents. Each agent is optimised for a distinct educational task — tutoring, quiz generation, curriculum design, answer evaluation, and document-grounded research.

The platform is powered by **Anthropic Claude** as its large language model (LLM) backbone, orchestrated via the **LangGraph** state-machine framework, and supplemented by a **Hybrid RAG (Retrieval-Augmented Generation)** pipeline that grounds answers in uploaded educational documents.

### Key Capabilities

| Capability | Description |
|---|---|
| Conversational Tutoring | Socratic, step-by-step concept explanations |
| Study Plan Generation | Personalised, week-by-week learning paths |
| Adaptive Quizzes | MCQ and short-answer quizzes with auto-scoring |
| Answer Evaluation | Structured feedback with score, grade, and improvement tips |
| Document Research | RAG-powered Q&A grounded in uploaded PDFs/TXTs |
| Hybrid Knowledge Retrieval | FAISS dense + BM25 sparse search fused via RRF |

---

## 2. Technologies Used

### 2.1 Core AI / LLM Stack

| Technology | Version | Role |
|---|---|---|
| **Anthropic Claude** (`claude-sonnet-4-20250514`) | API | Primary LLM for all agent reasoning and generation |
| **LangChain** | ≥ 0.3.0 | LLM abstraction layer, prompt templates, message types |
| **LangChain-Anthropic** | ≥ 0.3.0 | Anthropic-specific ChatAnthropic client |
| **LangChain-Community** | ≥ 0.3.0 | Document loaders (PyPDF, TextLoader), FAISS wrapper |
| **LangChain-Core** | ≥ 0.3.0 | `BaseMessage`, `AIMessage`, `HumanMessage`, `Document` |
| **LangGraph** | ≥ 0.2.0 | Multi-agent state machine & graph orchestration |

### 2.2 RAG / Retrieval Stack

| Technology | Version | Role |
|---|---|---|
| **FAISS (CPU)** | ≥ 1.8.0 | Dense semantic vector index |
| **BM25 (rank-bm25)** | ≥ 0.2.2 | Sparse keyword retrieval index |
| **Sentence-Transformers** | ≥ 3.0.0 | Local embedding model (`all-MiniLM-L6-v2`) |
| **LangChain-HuggingFace** | ≥ 0.1.0 | HuggingFace embedding integration |
| **PyPDF** | ≥ 4.0.0 | PDF document parsing |
| **ChromaDB** | ≥ 0.5.0 | Alternative vector store (available, not primary) |
| **tiktoken** | ≥ 0.7.0 | Token counting utilities |

### 2.3 Frontend / UI

| Technology | Version | Role |
|---|---|---|
| **Streamlit** | ≥ 1.40.0 | Web application UI framework |
| **streamlit-chat** | ≥ 0.1.1 | Chat UI components |

### 2.4 Utilities & Infrastructure

| Technology | Version | Role |
|---|---|---|
| **Python** | 3.13 | Runtime language |
| **python-dotenv** | ≥ 1.0.0 | `.env` API key management |
| **Pydantic** | ≥ 2.0.0 | Data validation and typing |
| **pickle** | stdlib | BM25 index persistence |
| **json / re** | stdlib | JSON parsing, regex extraction |

---

## 3. Technical Architecture

### 3.1 High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI (app.py)                    │
│   Sidebar │ Chat Tab │ Quiz Tab │ Research Tab │ Eval Tab   │
└─────────────────────┬───────────────────────────────────────┘
                      │ user_message + history + subject + level
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              EducationGraph (LangGraph)                     │
│                                                             │
│   START → [supervisor_node] → conditional_edge             │
│                   │                                         │
│     ┌─────────────┼────────────────────────┐               │
│     ▼             ▼             ▼           ▼       ▼       │
│ curriculum    tutor_node   quiz_node  evaluator  research   │
│  _node                                  _node    _node      │
│     └─────────────┴────────────────────────┴───────┘       │
│                        END                                  │
└───────────────────────────────┬─────────────────────────────┘
                                │ EducationState (TypedDict)
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                   Anthropic Claude API                      │
│              (ChatAnthropic – claude-sonnet-4)              │
└─────────────────────────────────────────────────────────────┘
                                ▲
                                │ context documents
┌─────────────────────────────────────────────────────────────┐
│                  RAG Pipeline                               │
│  AdvancedRetriever → MultiQuery Expansion                   │
│       ↓                                                     │
│  HybridVectorStore                                          │
│  ├── FAISS Dense Index  (semantic similarity)               │
│  └── BM25 Sparse Index  (keyword matching)                  │
│       ↓                                                     │
│  Reciprocal Rank Fusion (RRF) → top-k documents             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 LangGraph State Machine

The graph is defined in `graph/education_graph.py` using `StateGraph`.

**State Schema (`EducationState`):**

```python
class EducationState(TypedDict):
    messages:       Annotated[list[BaseMessage], add_messages]  # Full conversation
    current_agent:  str          # Agent name chosen by supervisor
    subject:        str          # Student's selected subject
    student_level:  str          # beginner | intermediate | advanced
    last_response:  str          # Final agent response text
    quiz_data:      dict         # Quiz state data
    metadata:       dict         # Routing metadata & diagnostics
```

**Graph Flow:**

```
START
  └─► supervisor_node
          │  (LLM classifies intent)
          ├─► curriculum  ─► END
          ├─► tutor       ─► END
          ├─► quiz        ─► END
          ├─► evaluator   ─► END
          └─► research    ─► END
```

Each leaf node invokes its specialist agent, writes the response into `last_response`, and terminates. The graph is compiled once and cached by Streamlit's `@st.cache_resource`.

### 3.3 Agent Architecture

All agents follow a unified pattern:

```
Agent Class
├── __init__(llm: ChatAnthropic)
├── handle(message, history) → str      ← called by the graph node
└── <domain methods>                    ← called directly by UI tabs
```

#### Supervisor Agent (`agents/supervisor_agent.py`)
- **Role:** Intent classifier / router
- **Method:** Sends the student message to Claude with a classification prompt listing the 5 valid agents; extracts the agent name from the response.
- **Fallback:** Defaults to `tutor` if the LLM response is ambiguous.

#### Tutor Agent (`agents/tutor_agent.py`)
- **Role:** Socratic concept explainer
- **Approach:** Uses the Socratic method — guiding questions, analogies, step-by-step breakdowns, comprehension checks.
- **History window:** Last 8 messages.

#### Curriculum Agent (`agents/curriculum_agent.py`)
- **Role:** Personalised learning path designer
- **Output format:** Structured plan with Overview, Prerequisites, Week-by-Week modules, Resources, and Milestones.
- **History window:** Last 6 messages.

#### Quiz Agent (`agents/quiz_agent.py`)
- **Role:** Adaptive quiz generator
- **Output:** Structured JSON — `quiz_title`, `subject`, `total_marks`, `questions[]` (each with `id`, `type`, `question`, `options`, `correct_answer`, `explanation`, `marks`, `difficulty`).
- **Difficulty mix:** 30% easy, 50% medium, 20% hard.
- **Types:** MCQ (4 options) and short-answer.
- **Parsing:** JSON extraction with regex fallback.

#### Evaluator Agent (`agents/evaluator_agent.py`)
- **Role:** Answer grader and feedback provider
- **Output:** Structured JSON — `score` (0–10), `grade` (A–F), `percentage`, `strengths[]`, `improvements[]`, `detailed_feedback`, `next_steps[]`, `model_answer`.
- **Display:** Visual score bar using block characters.

#### Research Agent (`agents/research_agent.py`)
- **Role:** Document-grounded Q&A
- **Method:** Retrieves up to 5 relevant document chunks via `AdvancedRetriever`, injects them as context into a system message, then queries Claude.
- **Fallback:** If context is insufficient, agent transparently falls back to general knowledge.

### 3.4 RAG Pipeline Architecture

```
User Query
    │
    ▼
[AdvancedRetriever.retrieve()]
    │
    ├─ Stage 1: Multi-Query Expansion
    │      LLM generates 3 query variants → [q0, q1, q2, q3]
    │
    ├─ Stage 2: Hybrid Search (per query variant)
    │      ├─ FAISS.similarity_search_with_score()  →  dense_ranked{}
    │      └─ BM25Okapi.get_scores()                →  sparse_ranked{}
    │
    ├─ Stage 3: Reciprocal Rank Fusion (RRF)
    │      score = λ/(60+dense_rank) + (1-λ)/(60+sparse_rank)
    │      λ = 0.6  (60% weight on dense retrieval)
    │
    └─ Stage 4: Deduplicate & return top-k Documents
```

**Embedding model:** `sentence-transformers/all-MiniLM-L6-v2` (local, CPU-based, no API key required).

**Persistence:** FAISS index is saved to `vector_db/faiss_index/`; BM25 index is pickled to `vector_db/bm25.pkl`.

**Document ingestion:**
- Supported formats: `.pdf`, `.txt`, `.md`
- Chunk size: 800 characters with 150-character overlap
- Splitter: `RecursiveCharacterTextSplitter`
- Built-in sample content: Mathematics (Calculus), Physics (Mechanics), Computer Science (DSA)

### 3.5 Session State Management

Streamlit `st.session_state` is used for all client-side state:

| Key | Type | Description |
|---|---|---|
| `messages` | `list[dict]` | Chat history: `{role, content, agent}` |
| `graph` | `EducationGraph` | The LangGraph instance |
| `rag_ready` | `bool` | Whether the vector index is loaded |
| `api_key` | `str` | Anthropic API key |
| `subject` | `str` | Selected subject |
| `level` | `str` | Student level |
| `quiz_state` | `dict` | Active quiz object |
| `agent_stats` | `dict` | Per-agent invocation counts for the session |

The graph is cached at the application level using `@st.cache_resource(...)`, keyed by `(api_key, model)`, so it survives Streamlit re-runs.

---

## 4. Business Architecture

### 4.1 Value Proposition

The platform addresses three core educational problems:

| Problem | Solution |
|---|---|
| One-size-fits-all instruction | Personalised learning plans and adaptive difficulty |
| Passive content delivery | Socratic dialogue and interactive quizzes |
| Lack of timely feedback | Immediate AI-powered answer evaluation with actionable guidance |

### 4.2 Stakeholders

| Stakeholder | Role | Interaction |
|---|---|---|
| **Student** | Primary user | Chat, quiz, upload documents, get study plans |
| **Educator / Faculty** | Content provider | Upload course PDFs to enrich the knowledge base |
| **Institution (IIT Patna)** | Platform owner | Configure model, deploy, monitor usage |
| **Anthropic** | LLM provider | API access to Claude models |

### 4.3 Business Process Flow

```
Student Arrives
    │
    ├─ Configures API key + subject + level (Sidebar)
    │
    ├─ STUDY PLANNING
    │       Student requests study plan → Curriculum Agent → Week-by-week plan
    │
    ├─ LEARNING
    │       Student asks concept question → Tutor Agent → Socratic explanation
    │
    ├─ SELF-ASSESSMENT
    │       Student requests quiz → Quiz Agent → MCQ/short-answer quiz
    │       Student submits answers → Quiz auto-grader OR Evaluator Agent
    │
    ├─ DEEP RESEARCH
    │       Student uploads PDF notes → Document Processor → Vector Index
    │       Student asks document question → Research Agent → Cited answer
    │
    └─ FEEDBACK LOOP
            Student submits written answer → Evaluator Agent → Score + feedback
            Student reviews next steps → returns to LEARNING
```

### 4.4 Agent Responsibility Matrix

| Agent | Trigger Keywords | Business Function |
|---|---|---|
| Supervisor | (every message) | Intent routing — reduces misrouting waste |
| Curriculum | "study plan", "learning path", "curriculum", "schedule" | Onboarding & learning roadmap |
| Tutor | "explain", "how", "why", "what is", "help me understand" | Core instructional delivery |
| Quiz | "quiz", "test me", "practice", "MCQ" | Self-assessment & retention |
| Evaluator | "evaluate", "grade my answer", "is this correct" | Formative assessment |
| Research | "what does the document say", "find in notes", deep topic | Knowledge-base grounded Q&A |

### 4.5 Scalability Considerations

- **Multi-tenancy:** The `@st.cache_resource` cache is keyed by API key + model, allowing different users with different keys to use isolated graph instances.
- **Vector index:** Persisted to disk (`vector_db/`); survives server restarts.
- **Model flexibility:** `config.json` supports switching between Anthropic, OpenAI, and Gemini models without code changes (OpenAI/Gemini integration can be extended).
- **Document scale:** Hybrid FAISS + BM25 handles hundreds of uploaded documents efficiently.

---

## 5. Module Reference

### File Structure

```
multi-agent-tutors/
│
├── app.py                        # Streamlit UI entry point
├── config.json                   # Model & provider configuration
├── requirements.txt              # Python dependencies
│
├── graph/
│   └── education_graph.py        # LangGraph state machine + EducationGraph class
│
├── agents/
│   ├── supervisor_agent.py       # Intent classifier / router
│   ├── tutor_agent.py            # Socratic explainer
│   ├── curriculum_agent.py       # Learning path designer
│   ├── quiz_agent.py             # Quiz generator + parser
│   ├── evaluator_agent.py        # Answer grader + feedback
│   └── research_agent.py        # RAG-powered Q&A agent
│
├── rag/
│   ├── vector_store.py           # HybridVectorStore (FAISS + BM25)
│   ├── advanced_retriever.py     # Multi-query + RRF retrieval pipeline
│   └── document_processor.py    # PDF/TXT ingestion, chunking, sample content
│
├── utils/
│   └── helpers.py                # load_api_key, format_agent_badge, AGENT_DESCRIPTIONS
│
├── sample_docs/                  # Default educational documents
└── vector_db/                    # Persisted FAISS & BM25 indices (auto-created)
```

### Key Classes & Methods

| Class | Module | Key Methods |
|---|---|---|
| `EducationGraph` | `graph/education_graph.py` | `run()`, `initialise_rag()`, `add_documents_to_rag()` |
| `EducationState` | `graph/education_graph.py` | TypedDict for LangGraph state |
| `SupervisorAgent` | `agents/supervisor_agent.py` | `route(message) → str` |
| `TutorAgent` | `agents/tutor_agent.py` | `explain()`, `handle()` |
| `CurriculumAgent` | `agents/curriculum_agent.py` | `create_learning_path()`, `handle()` |
| `QuizAgent` | `agents/quiz_agent.py` | `generate_quiz()`, `handle()`, `reveal_answers()` |
| `EvaluatorAgent` | `agents/evaluator_agent.py` | `evaluate()`, `format_result()` |
| `ResearchAgent` | `agents/research_agent.py` | `research()`, `get_sources()` |
| `HybridVectorStore` | `rag/vector_store.py` | `build()`, `load()`, `hybrid_search()`, `add_documents()` |
| `AdvancedRetriever` | `rag/advanced_retriever.py` | `retrieve()`, `simple_retrieve()`, `format_context()` |

---

## 6. Data Flow

### 6.1 Chat Message Flow

```
User types message in st.chat_input
    │
    ▼
_process_message(user_input)
    │
    ├─ Append to st.session_state.messages
    ├─ Build LangChain message history (HumanMessage / AIMessage)
    ├─ ensure_graph() → load EducationGraph from cache
    ├─ ensure_rag()   → load/build vector index
    │
    ▼
EducationGraph.run(user_message, history, subject, student_level)
    │
    ├─ Construct EducationState with full message history
    ├─ graph.invoke(initial_state)
    │       │
    │       ▼ supervisor_node
    │           LLM classifies → current_agent = "tutor" | "quiz" | ...
    │       ▼ <agent>_node
    │           Agent.handle(query, history) → response string
    │       ▼ END
    │
    ▼ Returns {"response": str, "agent": str}
    │
    ├─ Update agent_stats
    ├─ Append {"role": "assistant", "content": response, "agent": agent} to messages
    └─ st.rerun() → UI refreshes with new message
```

### 6.2 Document Upload & RAG Indexing Flow

```
User selects PDF/TXT files via st.file_uploader
    │
    ▼
_handle_uploads(uploaded_files)
    │
    ├─ Write files to temporary directory
    │
    ▼
EducationGraph.add_documents_to_rag(file_paths)
    │
    ├─ load_documents_from_files()  → List[Document]  (PyPDFLoader / TextLoader)
    ├─ chunk_documents()            → List[Document]  (800 chars / 150 overlap)
    │
    ▼
HybridVectorStore.add_documents(chunks)
    │
    ├─ FAISS.add_documents()       → updated dense index
    ├─ Rebuild BM25Okapi()         → updated sparse index
    └─ Save FAISS to vector_db/    → persisted
```

---

## 7. Configuration Reference

### `config.json`

```json
{
    "provider": "anthropicai",
    "anthropicai": {
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.7,
        "max_tokens": 1024
    },
    "huggingface": {
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
    }
}
```

| Key | Default | Description |
|---|---|---|
| `provider` | `"anthropicai"` | Active LLM provider |
| `anthropicai.model` | `"claude-sonnet-4-20250514"` | Claude model identifier |
| `anthropicai.temperature` | `0.7` | LLM sampling temperature |
| `anthropicai.max_tokens` | `1024` | Maximum output tokens per call |
| `huggingface.embedding_model` | `"all-MiniLM-L6-v2"` | Local embedding model for RAG |

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key (`sk-ant-…`). Can also be entered in the UI. |

Create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

---

## 8. User Manual

### 8.1 Starting the Application

```bash
# Activate virtual environment
.\myenv\Scripts\Activate.ps1          # Windows PowerShell

# Launch the app
streamlit run app.py
```

The browser will open automatically at `http://localhost:8501`.

---

### 8.2 Sidebar — First-Time Setup

#### Step 1: Enter Your API Key
- In the left sidebar, find **🔑 API Configuration**.
- Paste your **Anthropic API key** (starts with `sk-ant-`).
- A green ✅ confirmation will appear.
- Alternatively, add it to a `.env` file and it will load automatically.

#### Step 2: Set Your Student Profile
- **Subject Focus** — Select from: General, Mathematics, Physics, Computer Science, Machine Learning, Chemistry, Biology, History, Literature.
- **Learning Level** — Select: Beginner, Intermediate, or Advanced.

#### Step 3: Build the Knowledge Base (optional)
- Click **🔨 Build Knowledge Base** to index the built-in sample documents (Mathematics, Physics, Computer Science).
- Or upload your own study materials (see §8.6).

---

### 8.3 Tab 1 — 💬 Chat Tutor

This is the main conversational interface. Type any educational question in the chat box.

**Example prompts:**
- `"Explain gradient descent step by step"` → 🧑‍🏫 **Tutor Agent** responds with Socratic breakdown
- `"Create a 4-week study plan for Machine Learning"` → 📚 **Curriculum Agent** generates a weekly plan
- `"Quiz me on Python data structures"` → 📝 **Quiz Agent** generates a quiz in the chat
- `"Evaluate my answer: Newton's second law states F=ma"` → 📊 **Evaluator Agent** scores and gives feedback
- `"What does the document say about derivatives?"` → 🔍 **Research Agent** retrieves and cites from the knowledge base

**Quick Action Buttons** in the sidebar:
| Button | Action |
|---|---|
| 📚 Study Plan | Generates a study plan for your selected subject |
| 🔍 Deep Q&A | Asks the Research Agent about key concepts from documents |
| 📝 Quiz Me | Requests a quiz on your subject at your level |
| 💡 Explain | Asks the Tutor to explain a fundamental concept |

**Agent Badge:** Every AI response shows a colour badge identifying which agent answered (e.g., `🧑‍🏫 AI Tutor`, `📝 Quiz Master`).

**Session Stats** (sidebar): Shows how many times each agent has been used in the current session.

**Clear Chat:** Click 🗑️ **Clear Chat** in the sidebar to reset the conversation.

---

### 8.4 Tab 2 — 📝 Quiz Mode

A dedicated structured quiz interface.

**Steps:**
1. Enter a **Quiz Topic** (pre-filled with your selected subject).
2. Set the **Number of Questions** (3–10) using the slider.
3. Choose **Difficulty**: easy, medium, hard, or mixed.
4. Click **🎯 Generate Quiz**.
5. For each question:
   - **MCQ questions:** Select one of four radio button options.
   - **Short-answer questions:** Type your answer in the text box.
6. Click **✅ Submit & See Answers** to see:
   - ✅ / ❌ for each question
   - The correct answer
   - A brief explanation
   - Your final **score** (e.g., `4/5 (80%)`)
7. Scoring ≥ 80% triggers a 🎈 balloon celebration.

---

### 8.5 Tab 3 — 🔍 Research

Ask document-grounded questions with source citations.

**Steps:**
1. Type your research question in the text area.
2. Tick **Show retrieved sources** to see which document chunks were used.
3. Click **🔍 Research**.
4. The answer appears with:
   - **📖 Answer** — Claude's response grounded in your documents.
   - **📚 Sources Retrieved** — expandable cards showing each source file and a preview of the retrieved chunk.

> **Note:** The knowledge base must be built first (click **🔨 Build Knowledge Base** in the sidebar or upload documents).

---

### 8.6 Uploading Study Materials

1. In the sidebar under **📤 Upload Study Materials**, click **Browse files**.
2. Select one or more **PDF** or **TXT** files.
3. Click **📥 Index Documents**.
4. A success message shows how many chunks were indexed.
5. The **Research** tab and **Research Agent** will now use your documents.

**Tips:**
- Lecture notes, textbook chapters, and research papers work best.
- Multiple files can be uploaded at once.
- The index is persisted to disk — uploaded documents survive app restarts.

---

### 8.7 Tab 4 — 📊 Evaluator

Submit a written answer for detailed AI grading.

**Steps:**
1. Enter the **Question / Problem** in the left text area.
2. Type your **Answer** in the right text area.
3. Optionally, provide the **Expected Answer / Key Points** for more accurate grading.
4. Set the **Subject** field (pre-filled from your profile).
5. Click **📊 Evaluate My Answer**.
6. Results include:
   - **Score** (0–10) with visual bar `████████░░`
   - **Grade** (A / B / C / D / F) and **Percentage**
   - ✅ **Strengths** — what you got right
   - 🔧 **Areas to Improve** — gaps and misconceptions
   - 📝 **Detailed Feedback** — full AI explanation
   - 💡 **Model Answer** — the ideal response
   - 🚀 **Next Steps** — specific recommendations

---

### 8.8 Understanding Agent Routing

The **Supervisor Agent** automatically analyses your message and routes it to the best agent. You do not need to specify which agent to use. The routing logic is:

| If your message contains... | Routed to |
|---|---|
| "study plan", "learning path", "curriculum" | 📚 Curriculum Agent |
| "explain", "how does", "what is", "why" | 🧑‍🏫 Tutor Agent |
| "quiz", "test me", "practice questions" | 📝 Quiz Agent |
| "evaluate", "grade my answer", "check my answer" | 📊 Evaluator Agent |
| "what does the document say", deep research | 🔍 Research Agent |

---

## 9. Installation & Setup

### Prerequisites

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)
- Internet access (for Anthropic API calls)

### Steps

```bash
# 1. Clone the repository
git clone <repo-url>
cd multi-agent-tutors

# 2. Create and activate virtual environment
python -m venv myenv
.\myenv\Scripts\Activate.ps1       # Windows PowerShell
# source myenv/bin/activate         # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your API key
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" > .env

# 5. Launch the app
streamlit run app.py
```

The application opens at **http://localhost:8501**.

---

## 10. Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: streamlit` | Wrong Python / not in venv | Use `.\myenv\Scripts\streamlit.exe run app.py` |
| `ModuleNotFoundError: langchain_core` | Running with `python app.py` | Use `streamlit run app.py` (not `python app.py`) |
| `pip install` network error | Corporate proxy or no internet | Configure pip proxy or install from offline wheel |
| `❌ Error: Could not connect to Anthropic` | Invalid API key | Re-enter your `sk-ant-…` key in the sidebar |
| Quiz shows raw text, not structured | Claude returned non-JSON | Retry; the agent has a regex JSON extraction fallback |
| Knowledge base shows "not ready" | RAG not initialised | Click **🔨 Build Knowledge Base** in the sidebar |
| FAISS load error on restart | Corrupted `vector_db/` | Delete `vector_db/` folder and rebuild the index |
| Slow first response | Embedding model loading | `all-MiniLM-L6-v2` loads once at startup; subsequent calls are fast |

---

*Document generated for IIT Patna — Multi-Agent AI Education Platform v1.0*
