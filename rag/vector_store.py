"""
Vector Store – wraps FAISS (dense) + BM25 (sparse) in a unified hybrid store.
"""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import List, Optional

import numpy as np
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS
from rank_bm25 import BM25Okapi

# ---------------------------------------------------------------------------
# Offline TF-IDF + SVD embeddings (no internet / model download required)
# ---------------------------------------------------------------------------

class TFIDFEmbeddings(Embeddings):
    """
    Fully offline embeddings using TF-IDF vectorisation followed by
    Truncated SVD (LSA) to produce dense fixed-dimension vectors.

    Requires only scikit-learn (already installed).
    Quality is lower than sentence-transformers but works with zero network
    access and no pre-downloaded model files.
    """

    DIM = 384  # output dimension – matches all-MiniLM-L6-v2 for FAISS compatibility

    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD
        self._vectorizer = TfidfVectorizer(
            max_features=8000, sublinear_tf=True, ngram_range=(1, 2)
        )
        self._svd = TruncatedSVD(n_components=self.DIM, random_state=42)
        self._fitted = False
        self._actual_dim = self.DIM

    # ------------------------------------------------------------------
    def _fit_on(self, texts: List[str]) -> None:
        from sklearn.decomposition import TruncatedSVD
        tfidf = self._vectorizer.fit_transform(texts)
        # SVD needs n_components < min(rows, cols)
        max_comp = min(self.DIM, tfidf.shape[0] - 1, tfidf.shape[1] - 1)
        self._actual_dim = max(1, max_comp)
        self._svd = TruncatedSVD(n_components=self._actual_dim, random_state=42)
        self._svd.fit(tfidf)
        self._fitted = True

    def _to_vectors(self, texts: List[str]) -> List[List[float]]:
        tfidf = self._vectorizer.transform(texts)
        vecs = self._svd.transform(tfidf)  # (n, actual_dim)
        # Pad to DIM so FAISS index dimension stays consistent
        if vecs.shape[1] < self.DIM:
            vecs = np.pad(vecs, ((0, 0), (0, self.DIM - vecs.shape[1])))
        # L2-normalise
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (vecs / norms).tolist()

    # ------------------------------------------------------------------
    # LangChain Embeddings interface
    # ------------------------------------------------------------------
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self._fitted:
            self._fit_on(texts)
        return self._to_vectors(texts)

    def embed_query(self, text: str) -> List[float]:
        if not self._fitted:
            # No corpus to fit on yet – return zero vector
            return [0.0] * self.DIM
        return self._to_vectors([text])[0]


# ---------------------------------------------------------------------------
# Embedding factory
# ---------------------------------------------------------------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Prevent HuggingFace from making any network calls
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")


def _get_embeddings() -> Embeddings:
    """
    Try to load the local sentence-transformer model first (requires the
    model files to be cached in ~/.cache/huggingface/).
    If not available, fall back to the offline TF-IDF embeddings.
    """
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        emb = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu", "local_files_only": True},
            encode_kwargs={"normalize_embeddings": True},
        )
        print("[VectorStore] Using sentence-transformer embeddings.")
        return emb
    except Exception as exc:
        print(f"[VectorStore] sentence-transformer not available ({type(exc).__name__}). "
              "Falling back to offline TF-IDF embeddings.")
        return TFIDFEmbeddings()


# ---------------------------------------------------------------------------
# Hybrid Vector Store
# ---------------------------------------------------------------------------

class HybridVectorStore:
    """
    Combines FAISS (semantic) and BM25 (keyword) retrieval.
    Scores are fused via Reciprocal Rank Fusion (RRF).

    Embeddings are loaded lazily – the model is only initialised the first
    time build() or load() is actually called, so the graph can be created
    even when the embedding model is not yet available.
    """

    def __init__(self, persist_dir: str = "vector_db"):
        self.persist_dir = Path(persist_dir)
        self.faiss_store: Optional[FAISS] = None
        self.bm25_index: Optional[BM25Okapi] = None
        self.bm25_docs: List[Document] = []
        self._embeddings = None          # loaded lazily

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = _get_embeddings()
        return self._embeddings

    # ------------------------------------------------------------------
    # Build / persist
    # ------------------------------------------------------------------

    def build(self, documents: List[Document]) -> None:
        """Index a list of Document chunks."""
        print(f"[VectorStore] Indexing {len(documents)} chunks …")

        # FAISS dense index
        self.faiss_store = FAISS.from_documents(documents, self.embeddings)

        # BM25 sparse index
        self.bm25_docs = documents
        tokenised = [doc.page_content.lower().split() for doc in documents]
        self.bm25_index = BM25Okapi(tokenised)

        # Persist
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.faiss_store.save_local(str(self.persist_dir / "faiss_index"))
        with open(self.persist_dir / "bm25.pkl", "wb") as f:
            pickle.dump((self.bm25_index, self.bm25_docs), f)

        print("[VectorStore] Index built and persisted.")

    def load(self) -> bool:
        """Try to load a previously persisted index. Returns True on success."""
        faiss_path = self.persist_dir / "faiss_index"
        bm25_path = self.persist_dir / "bm25.pkl"

        if not faiss_path.exists() or not bm25_path.exists():
            return False

        try:
            # Load BM25 first so we can re-fit TFIDFEmbeddings if needed
            with open(bm25_path, "rb") as f:
                self.bm25_index, self.bm25_docs = pickle.load(f)

            # If using TFIDFEmbeddings, re-fit on the stored corpus texts so
            # that embed_query works correctly after loading from disk.
            emb = self.embeddings
            if isinstance(emb, TFIDFEmbeddings) and not emb._fitted and self.bm25_docs:
                texts = [doc.page_content for doc in self.bm25_docs]
                emb._fit_on(texts)

            self.faiss_store = FAISS.load_local(
                str(faiss_path),
                emb,
                allow_dangerous_deserialization=True,
            )
            print("[VectorStore] Loaded persisted index.")
            return True
        except Exception as exc:
            print(f"[VectorStore] Could not load index: {exc}")
            return False

    def add_documents(self, documents: List[Document]) -> None:
        """Add new documents to an existing index."""
        if self.faiss_store is None:
            self.build(documents)
            return

        self.faiss_store.add_documents(documents)
        self.bm25_docs.extend(documents)
        tokenised = [doc.page_content.lower().split() for doc in self.bm25_docs]
        self.bm25_index = BM25Okapi(tokenised)
        self.faiss_store.save_local(str(self.persist_dir / "faiss_index"))

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def hybrid_search(
        self,
        query: str,
        k: int = 6,
        lambda_param: float = 0.6,
    ) -> List[Document]:
        """
        Hybrid RRF search.
        lambda_param: weight for dense scores (1-lambda for sparse).
        """
        if self.faiss_store is None:
            return []

        # --- Dense retrieval ---
        dense_results = self.faiss_store.similarity_search_with_score(query, k=k * 2)
        dense_ranked = {doc.page_content: rank for rank, (doc, _) in enumerate(dense_results)}

        # --- Sparse BM25 retrieval ---
        tokenised_query = query.lower().split()
        bm25_scores = self.bm25_index.get_scores(tokenised_query)
        bm25_top_idx = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[: k * 2]
        sparse_ranked = {self.bm25_docs[i].page_content: rank for rank, i in enumerate(bm25_top_idx)}

        # --- Reciprocal Rank Fusion ---
        rrf_scores: dict[str, float] = {}
        all_contents = set(dense_ranked) | set(sparse_ranked)
        for content in all_contents:
            dense_r = dense_ranked.get(content, k * 2) + 1
            sparse_r = sparse_ranked.get(content, k * 2) + 1
            rrf_scores[content] = lambda_param / (60 + dense_r) + (1 - lambda_param) / (60 + sparse_r)

        # Collect and return top-k Documents
        sorted_contents = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:k]
        content_to_doc = {doc.page_content: doc for doc, _ in dense_results}
        for i in bm25_top_idx:
            content_to_doc[self.bm25_docs[i].page_content] = self.bm25_docs[i]

        return [content_to_doc[c] for c in sorted_contents if c in content_to_doc]

    def as_retriever(self, k: int = 6):
        """Return a LangChain-compatible retriever backed by FAISS."""
        if self.faiss_store is None:
            raise RuntimeError("Vector store not initialised. Call build() or load() first.")
        return self.faiss_store.as_retriever(search_kwargs={"k": k})

    @property
    def is_ready(self) -> bool:
        return self.faiss_store is not None
