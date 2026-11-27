"""Semantic document recommendation engine for Umbral Web."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from fastembed import TextEmbedding
from sklearn.metrics.pairwise import cosine_similarity

if __package__:
    from .classifier import Document
    from .retrieval import RetrievalEngine
else:
    from classifier import Document
    from retrieval import RetrievalEngine


MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSION = 384
DEFAULT_MIN_SIMILARITY = 0.55


@dataclass(frozen=True)
class SemanticRecommendation:
    """A semantically related document and its explanation."""

    document: Document
    similarity: float
    shared_terms: tuple[str, ...]
    explanation: str


class SemanticRecommendationEngine:
    """Recommend documents using contextual text embeddings."""

    def __init__(
        self,
        retrieval_engine: RetrievalEngine | None = None,
        embedding_model=None,
    ) -> None:

        self.retrieval = (
            retrieval_engine
            if retrieval_engine is not None
            else RetrievalEngine()
        )

        self.model = (
            embedding_model
            if embedding_model is not None
            else TextEmbedding(
                model_name=MODEL_NAME,
                threads=2,
            )
        )

        self.documents = self.retrieval.documents

        self.document_indices = {
            document.doc_id: index
            for index, document in enumerate(
                self.documents
            )
        }

        self.feature_names = (
            self.retrieval.vectorizer.get_feature_names_out()
        )

        document_texts = [
            f"{document.title}\n{document.text}"
            for document in self.documents
        ]

        self.document_embeddings = np.asarray(
            list(
                self.model.embed(
                    document_texts,
                    batch_size=4,
                )
            ),
            dtype=np.float32,
        )

        self._validate_embeddings(
            self.document_embeddings,
            len(self.documents),
        )

    @staticmethod
    def _validate_embeddings(
        embeddings,
        expected_rows: int,
    ) -> None:

        expected_shape = (
            expected_rows,
            EMBEDDING_DIMENSION,
        )

        if embeddings.shape != expected_shape:

            raise ValueError(
                f"Unexpected embedding shape: "
                f"{embeddings.shape}. "
                f"Expected {expected_shape}."
            )

        if not np.isfinite(embeddings).all():

            raise ValueError(
                "Embeddings contain invalid numeric values."
            )

        if np.any(
            np.linalg.norm(embeddings, axis=1) == 0
        ):

            raise ValueError(
                "Embeddings contain zero-length vectors."
            )

    @staticmethod
    def _validate_parameters(
        top_k: int,
        min_similarity: float,
    ) -> None:

        if (
            not isinstance(top_k, int)
            or isinstance(top_k, bool)
            or top_k < 1
        ):

            raise ValueError(
                "top_k must be a positive integer."
            )

        if (
            not math.isfinite(min_similarity)
            or not 0.0 <= min_similarity <= 1.0
        ):

            raise ValueError(
                "min_similarity must be between 0 and 1."
            )

    def _shared_terms(
        self,
        source_vector,
        target_index: int,
        limit: int = 5,
    ) -> tuple[str, ...]:
        """Return supplementary lexical evidence."""

        target_vector = (
            self.retrieval.document_matrix[target_index]
        )

        overlap = (
            source_vector
            .multiply(target_vector)
            .tocsr()
        )

        overlap.eliminate_zeros()

        if overlap.nnz == 0:
            return ()

        ranked_positions = np.argsort(
            overlap.data
        )[::-1]

        return tuple(
            str(
                self.feature_names[
                    overlap.indices[position]
                ]
            )
            for position in ranked_positions[:limit]
        )

    def _build_recommendations(
        self,
        source_embedding,
        source_lexical_vector,
        top_k: int,
        min_similarity: float,
        context: str,
        excluded_index: int | None = None,
    ) -> list[SemanticRecommendation]:

        similarities = cosine_similarity(
            source_embedding,
            self.document_embeddings,
        )[0]

        ranked_indices = sorted(
            range(len(self.documents)),
            key=lambda index: (
                -float(similarities[index]),
                self.documents[index].doc_id,
            ),
        )

        recommendations = []

        for index in ranked_indices:

            if index == excluded_index:
                continue

            similarity = float(
                np.clip(
                    similarities[index],
                    -1.0,
                    1.0,
                )
            )

            if similarity <= 0:
                continue

            if similarity < min_similarity:
                continue

            document = self.documents[index]

            terms = self._shared_terms(
                source_lexical_vector,
                index,
            )

            explanation = (
                f"Recommended based on semantic "
                f"embedding similarity to {context} "
                f"using {MODEL_NAME}."
            )

            if terms:

                explanation += (
                    " Supplementary shared lexical terms: "
                    f"{', '.join(terms)}."
                )

            else:

                explanation += (
                    " No shared lexical terms were found "
                    "in the TF-IDF vocabulary."
                )

            recommendations.append(
                SemanticRecommendation(
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
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
    ) -> list[SemanticRecommendation]:
        """Recommend semantically related documents."""

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

        source_embedding = (
            self.document_embeddings[
                source_index:source_index + 1
            ]
        )

        source_lexical_vector = (
            self.retrieval.document_matrix[source_index]
        )

        return self._build_recommendations(
            source_embedding=source_embedding,
            source_lexical_vector=source_lexical_vector,
            top_k=top_k,
            min_similarity=min_similarity,
            context=f"document {document_id}",
            excluded_index=source_index,
        )

    def recommend_by_query(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
    ) -> list[SemanticRecommendation]:
        """Recommend documents related to a search context."""

        self._validate_parameters(
            top_k,
            min_similarity,
        )

        query = query.strip()

        if not query:
            return []

        query_embedding = np.asarray(
            list(
                self.model.query_embed([query])
            ),
            dtype=np.float32,
        )

        self._validate_embeddings(
            query_embedding,
            expected_rows=1,
        )

        query_lexical_vector = (
            self.retrieval.vectorizer.transform(
                [query]
            )
        )

        return self._build_recommendations(
            source_embedding=query_embedding,
            source_lexical_vector=query_lexical_vector,
            top_k=top_k,
            min_similarity=min_similarity,
            context="the search query",
        )