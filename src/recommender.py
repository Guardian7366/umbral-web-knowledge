"""Document recommendation system for Umbral Web."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

if __package__:
    from .classifier import Document
    from .retrieval import RetrievalEngine
else:
    from classifier import Document
    from retrieval import RetrievalEngine


@dataclass(frozen=True)
class Recommendation:
    """A recommended document and its supporting information."""

    document: Document
    similarity: float
    shared_terms: tuple[str, ...]
    explanation: str


class RecommendationEngine:
    """Recommend documents using shared retrieval infrastructure."""

    def __init__(
        self,
        retrieval_engine: RetrievalEngine | None = None,
    ) -> None:

        self.retrieval = (
            retrieval_engine
            if retrieval_engine is not None
            else RetrievalEngine()
        )

        self.document_indices = {
            document.doc_id: index
            for index, document in enumerate(
                self.retrieval.documents
            )
        }

        self.feature_names = (
            self.retrieval.vectorizer.get_feature_names_out()
        )

    @staticmethod
    def _validate_parameters(
        top_k: int,
        min_similarity: float,
    ) -> None:

        if top_k < 1:
            raise ValueError(
                "top_k must be greater than zero."
            )

        if not 0.0 <= min_similarity <= 1.0:
            raise ValueError(
                "min_similarity must be between 0 and 1."
            )

    def _shared_terms(
        self,
        source_vector,
        target_vector,
        limit: int = 5,
    ) -> tuple[str, ...]:

        overlap = (
            source_vector
            .multiply(target_vector)
            .tocsr()
        )

        if overlap.nnz == 0:
            return ()

        ranked_positions = np.argsort(
            overlap.data
        )[::-1]

        terms = []

        for position in ranked_positions[:limit]:
            feature_index = overlap.indices[position]
            terms.append(
                str(self.feature_names[feature_index])
            )

        return tuple(terms)

    def _build_recommendations(
        self,
        source_vector,
        similarities,
        top_k: int,
        min_similarity: float,
        context: str,
        excluded_index: int | None = None,
    ) -> list[Recommendation]:

        ranked_indices = np.argsort(
            similarities
        )[::-1]

        recommendations = []

        for index in ranked_indices:

            if index == excluded_index:
                continue

            similarity = float(similarities[index])

            if similarity <= 0:
                continue

            if similarity < min_similarity:
                continue

            document = self.retrieval.documents[index]

            terms = self._shared_terms(
                source_vector,
                self.retrieval.document_matrix[index],
            )

            if terms:
                explanation = (
                    f"Recommended based on {context}. "
                    f"Shared relevant terms: "
                    f"{', '.join(terms)}."
                )
            else:
                explanation = (
                    f"Recommended based on {context} "
                    f"using cosine similarity."
                )

            recommendations.append(
                Recommendation(
                    document=document,
                    similarity=similarity,
                    shared_terms=terms,
                    explanation=explanation,
                )
            )

            if len(recommendations) >= top_k:
                break

        return recommendations

    def recommend_by_document(
        self,
        document_id: str,
        top_k: int = 3,
        min_similarity: float = 0.0,
    ) -> list[Recommendation]:
        """Recommend documents related to a selected document."""

        self._validate_parameters(
            top_k,
            min_similarity,
        )

        document_id = document_id.strip().upper()

        if document_id not in self.document_indices:
            raise ValueError(
                f"Unknown document ID: {document_id}"
            )

        source_index = self.document_indices[
            document_id
        ]

        source_vector = (
            self.retrieval.document_matrix[source_index]
        )

        similarities = cosine_similarity(
            source_vector,
            self.retrieval.document_matrix,
        )[0]

        return self._build_recommendations(
            source_vector=source_vector,
            similarities=similarities,
            top_k=top_k,
            min_similarity=min_similarity,
            context=f"document {document_id}",
            excluded_index=source_index,
        )

    def recommend_by_query(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.0,
    ) -> list[Recommendation]:
        """Recommend documents based on search context."""

        self._validate_parameters(
            top_k,
            min_similarity,
        )

        if not query.strip():
            return []

        query_vector = (
            self.retrieval.vectorizer.transform([query])
        )

        similarities = cosine_similarity(
            query_vector,
            self.retrieval.document_matrix,
        )[0]

        return self._build_recommendations(
            source_vector=query_vector,
            similarities=similarities,
            top_k=top_k,
            min_similarity=min_similarity,
            context="the search query",
        )