"""Shared document retrieval engine for Umbral Web."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

if __package__:
    from .classifier import Document, load_documents, build_vectorizer
else:
    from classifier import Document, load_documents, build_vectorizer


@dataclass(frozen=True)
class SearchResult:
    """A retrieved document and its similarity score."""

    document: Document
    similarity: float


class RetrievalEngine:
    """Reusable TF-IDF and cosine similarity retrieval engine."""

    def __init__(self) -> None:
        self.documents = load_documents()
        self.vectorizer = build_vectorizer()

        self.document_matrix = self.vectorizer.fit_transform(
            [document.text for document in self.documents]
        )

    def search(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[SearchResult]:
        """Return the most relevant documents for a query."""

        if top_k < 1:
            raise ValueError("top_k must be greater than zero.")

        if not query.strip():
            return []

        query_vector = self.vectorizer.transform([query])

        similarities = cosine_similarity(
            query_vector,
            self.document_matrix,
        )[0]

        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [
            SearchResult(
                document=self.documents[index],
                similarity=float(similarities[index]),
            )
            for index in top_indices
            if similarities[index] > 0
        ]