
# 🎓 Multi-Agent AI Education System

A production-grade, real-time AI-powered education platform built with:
- **Anthropic Claude** (claude-sonnet-4) – Core LLM
- **LangChain** – LLM orchestration & advanced RAG pipeline
- **LangGraph** – Multi-agent state machine orchestration
- **Streamlit** – Interactive UI

---

## 🏗️ Architecture

```
multi-agent-tutors/
├── app.py                      ← Streamlit UI (main entry point)
├── requirements.txt
├── .env.example
├── agents/
│   ├── __init__.py
│   ├── supervisor_agent.py     ← Routes queries to specialist agents
│   ├── curriculum_agent.py     ← Builds personalized learning paths
│   ├── tutor_agent.py          ← Explains concepts step-by-step
│   ├── quiz_agent.py           ← Generates adaptive quizzes
│   ├── evaluator_agent.py      ← Evaluates answers & gives feedback
│   └── research_agent.py       ← RAG-powered deep knowledge retrieval
├── graph/
│   ├── __init__.py
│   └── education_graph.py      ← LangGraph multi-agent workflow
├── rag/
│   ├── __init__.py
│   ├── document_processor.py   ← PDF/text ingestion & chunking
│   ├── advanced_retriever.py   ← Multi-query + hybrid search + reranking
│   └── vector_store.py         ← FAISS + BM25 hybrid vector store
├── utils/
│   ├── __init__.py
│   └── helpers.py
└── sample_docs/                ← Drop PDF/TXT educational materials here
```

## 🤖 Agents

| Agent | Role |
|---|---|
| **Supervisor** | Analyses intent & routes to the right specialist |
| **Curriculum** | Creates adaptive learning plans for any subject |
| **Tutor** | Socratic step-by-step explanation engine |
| **Quiz** | Generates MCQ / short-answer / coding quizzes |
| **Evaluator** | Scores student answers with detailed feedback |
| **Research** | RAG over uploaded documents for deep Q&A |

## 🔍 Advanced RAG Pipeline

1. **Document Processing** – PDF/TXT chunking with overlap
2. **Hybrid Indexing** – FAISS (semantic) + BM25 (keyword) dual index
3. **Multi-Query Retrieval** – Generates 3 query variants per question
4. **Contextual Compression** – Filters retrieved chunks for relevance
5. **Reranking** – Cross-encoder reranks final candidates
6. **Answer Synthesis** – Claude synthesises a grounded answer

## 🚀 Quick Start

```bash
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your API key
copy .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 4. (Optional) Add educational PDFs to sample_docs/

# 5. Launch the app
streamlit run app.py
```

## 🔑 Environment Variables

```
ANTHROPIC_API_KEY=your_key_here
```
