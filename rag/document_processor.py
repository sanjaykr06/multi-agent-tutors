
"""
Document Processor – handles PDF/TXT ingestion, cleaning, and
smart recursive chunking with overlap for the RAG pipeline.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def load_documents_from_directory(directory: str) -> List[Document]:
    """Load all supported documents from *directory* recursively."""
    docs: List[Document] = []
    path = Path(directory)

    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return docs

    for file_path in path.rglob("*"):
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            loaded = _load_single_file(str(file_path))
            docs.extend(loaded)
            print(f"[DocumentProcessor] Loaded {len(loaded)} pages from {file_path.name}")
        except Exception as exc:
            print(f"[DocumentProcessor] WARNING – could not load {file_path}: {exc}")

    return docs


def load_documents_from_files(file_paths: List[str]) -> List[Document]:
    """Load a specific list of file paths."""
    docs: List[Document] = []
    for fp in file_paths:
        try:
            loaded = _load_single_file(fp)
            docs.extend(loaded)
        except Exception as exc:
            print(f"[DocumentProcessor] WARNING – {fp}: {exc}")
    return docs


def chunk_documents(
    documents: List[Document],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> List[Document]:
    """Split documents into overlapping chunks and enrich metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    chunks = splitter.split_documents(documents)

    # Enrich each chunk with a sequential id and cleaned content
    for idx, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = idx
        chunk.metadata.setdefault("source", "unknown")
        chunk.page_content = _clean_text(chunk.page_content)

    # Remove near-empty chunks
    chunks = [c for c in chunks if len(c.page_content.strip()) > 50]
    print(f"[DocumentProcessor] Created {len(chunks)} chunks from {len(documents)} documents.")
    return chunks


# ---------------------------------------------------------------------------
# Built-in sample educational content
# ---------------------------------------------------------------------------

SAMPLE_CONTENT = {
    "mathematics": """
# Introduction to Calculus

## Limits and Continuity
A limit describes the value a function approaches as the input approaches a point.
The formal epsilon-delta definition: lim(x→a) f(x) = L means for every ε > 0 there
exists δ > 0 such that |f(x) − L| < ε whenever 0 < |x − a| < δ.

## Derivatives
The derivative f'(x) = lim(h→0) [f(x+h) − f(x)] / h measures the instantaneous rate
of change. Key rules: power rule, product rule, quotient rule, chain rule.
- Power rule: d/dx [x^n] = n·x^(n-1)
- Chain rule: d/dx [f(g(x))] = f'(g(x))·g'(x)

## Integration
Integration is the inverse of differentiation. The fundamental theorem of calculus
connects the two: ∫[a,b] f(x)dx = F(b) − F(a) where F' = f.
Techniques include substitution, integration by parts, and partial fractions.
""",
    "physics": """
# Classical Mechanics

## Newton's Laws of Motion
1. An object at rest stays at rest; an object in motion stays in motion unless acted
   upon by an external net force (Law of Inertia).
2. F = ma — net force equals mass times acceleration.
3. For every action there is an equal and opposite reaction.

## Energy and Work
Work W = F·d·cos(θ). Kinetic energy KE = ½mv². Potential energy PE = mgh.
The work-energy theorem: net work done on an object equals its change in kinetic energy.
Conservation of energy: total mechanical energy is conserved in the absence of
non-conservative forces.

## Waves and Oscillations
Simple harmonic motion: x(t) = A·cos(ωt + φ). Period T = 2π/ω.
Wave speed v = fλ where f is frequency and λ is wavelength.
""",
    "computer_science": """
# Data Structures and Algorithms

## Arrays and Linked Lists
Arrays provide O(1) random access but O(n) insertion/deletion.
Linked lists provide O(1) insertion/deletion at head but O(n) random access.

## Trees
Binary Search Tree (BST): left child < parent < right child.
Average operations O(log n), worst case O(n) for unbalanced trees.
Balanced trees (AVL, Red-Black) guarantee O(log n) for all operations.

## Sorting Algorithms
- Bubble Sort: O(n²) time, O(1) space — simple but slow.
- Merge Sort: O(n log n) time, O(n) space — divide and conquer.
- Quick Sort: O(n log n) average, O(n²) worst, O(log n) space — fast in practice.
- Heap Sort: O(n log n) time, O(1) space.

## Graph Algorithms
BFS explores level by level using a queue (O(V+E)).
DFS explores depth-first using a stack/recursion (O(V+E)).
Dijkstra's algorithm finds shortest paths in weighted graphs O((V+E) log V).
""",
    "machine_learning": """
# Machine Learning Fundamentals

## Supervised Learning
The model learns a mapping f: X → Y from labelled training examples.
- Regression: predicts continuous values (Linear Regression, SVR, Neural Networks).
- Classification: predicts discrete labels (Logistic Regression, SVM, Decision Trees).

Loss functions: MSE for regression, Cross-Entropy for classification.
Optimization: Gradient Descent – θ ← θ − α·∇L(θ).

## Overfitting and Regularisation
Overfitting occurs when a model memorises training data and fails to generalise.
Techniques: L1/L2 regularisation, Dropout, Early Stopping, Data Augmentation.

## Neural Networks
A neural network is composed of layers of neurons with learnable weights.
Activation functions: ReLU, Sigmoid, Tanh, Softmax.
Backpropagation computes gradients via the chain rule.

## Evaluation Metrics
Classification: Accuracy, Precision, Recall, F1-Score, ROC-AUC.
Regression: MAE, MSE, RMSE, R².
""",
}


def create_sample_documents() -> List[Document]:
    """Return a set of built-in educational documents when no files are available."""
    docs: List[Document] = []
    for subject, content in SAMPLE_CONTENT.items():
        docs.append(
            Document(
                page_content=content.strip(),
                metadata={"source": f"sample_{subject}", "subject": subject},
            )
        )
    return docs


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _load_single_file(file_path: str) -> List[Document]:
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext in {".txt", ".md"}:
        loader = TextLoader(file_path, encoding="utf-8")
    else:
        raise ValueError(f"Unsupported extension: {ext}")
    return loader.load()


def _clean_text(text: str) -> str:
    """Remove excessive whitespace and non-printable characters."""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\x20-\x7E\n]", " ", text)
    return text.strip()


