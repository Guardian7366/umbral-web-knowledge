"""Automated tests for the semantic recommendation engine."""

import unittest

import numpy as np

from src.retrieval import RetrievalEngine
from src.recommender import RecommendationEngine

from src.semantic_recommender import (
    SemanticRecommendationEngine,
    DEFAULT_MIN_SIMILARITY,
    EMBEDDING_DIMENSION,
    MODEL_NAME,
)


class TestSemanticRecommendationEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.retrieval = RetrievalEngine()

        cls.lexical = RecommendationEngine(
            cls.retrieval
        )

        cls.engine = SemanticRecommendationEngine(
            cls.retrieval
        )

    def test_document_collection(self):
        self.assertEqual(
            len(self.engine.documents), 9
        )

    def test_shared_retrieval_engine(self):
        self.assertIs(
            self.engine.retrieval,
            self.retrieval,
        )

    def test_embedding_dimensions(self):
        self.assertEqual(
            self.engine.document_embeddings.shape,
            (9, EMBEDDING_DIMENSION),
        )

    def test_embedding_values(self):
        embeddings = self.engine.document_embeddings

        self.assertTrue(
            np.isfinite(embeddings).all()
        )

        self.assertTrue(
            np.all(
                np.linalg.norm(
                    embeddings,
                    axis=1,
                ) > 0
            )
        )

    def test_semantic_query_baselines(self):
        cases = (
            (
                "How can we brainstorm new concepts as a team?",
                "UW04",
            ),
            (
                "How can moving interface elements improve usability?",
                "UW02",
            ),
            (
                "How can we validate an early design before building it?",
                "UW05",
            ),
            (
                "How can reusable layouts maintain a consistent brand?",
                "UW03",
            ),
            (
                "What lessons were learned from the Aula Clara course catalog?",
                "UW07",
            ),
        )

        for query, expected in cases:

            with self.subTest(query=query):

                results = self.engine.recommend_by_query(
                    query
                )

                self.assertTrue(results)

                self.assertEqual(
                    results[0].document.doc_id,
                    expected,
                )

    def test_semantic_improvement_over_lexical(self):
        query = (
            "How can we brainstorm "
            "new concepts as a team?"
        )

        lexical_results = (
            self.lexical.recommend_by_query(query)
        )

        semantic_results = (
            self.engine.recommend_by_query(query)
        )

        lexical_ids = [
            item.document.doc_id
            for item in lexical_results
        ]

        self.assertNotIn(
            "UW04",
            lexical_ids,
        )

        self.assertTrue(semantic_results)

        self.assertEqual(
            semantic_results[0].document.doc_id,
            "UW04",
        )

    def test_document_recommendation_baselines(self):
        cases = {
            "UW02": ["UW01", "UW08", "UW03"],
            "UW04": ["UW05", "UW06", "UW03"],
            "UW07": ["UW09", "UW08", "UW03"],
        }

        for document_id, expected in cases.items():

            with self.subTest(document_id=document_id):

                results = (
                    self.engine.recommend_by_document(
                        document_id
                    )
                )

                identifiers = [
                    item.document.doc_id
                    for item in results
                ]

                self.assertEqual(
                    identifiers,
                    expected,
                )

    def test_source_document_is_excluded(self):
        for document in self.engine.documents:

            with self.subTest(
                document_id=document.doc_id
            ):

                results = (
                    self.engine.recommend_by_document(
                        document.doc_id,
                        top_k=9,
                        min_similarity=0.0,
                    )
                )

                self.assertNotIn(
                    document.doc_id,
                    [
                        item.document.doc_id
                        for item in results
                    ],
                )

    def test_document_id_normalization(self):
        original = (
            self.engine.recommend_by_document(
                "UW04"
            )
        )

        normalized = (
            self.engine.recommend_by_document(
                " uw04 "
            )
        )

        self.assertEqual(
            original,
            normalized,
        )

    def test_similarity_order(self):
        results = self.engine.recommend_by_document(
            "UW04",
            top_k=8,
            min_similarity=0.0,
        )

        self.assertTrue(results)

        scores = [
            item.similarity
            for item in results
        ]

        self.assertEqual(
            scores,
            sorted(scores, reverse=True),
        )

    def test_similarity_range(self):
        results = self.engine.recommend_by_document(
            "UW04",
            top_k=8,
            min_similarity=0.0,
        )

        self.assertTrue(results)

        for item in results:

            self.assertGreater(
                item.similarity, 0.0
            )

            self.assertLessEqual(
                item.similarity, 1.0
            )

    def test_default_threshold(self):
        results = self.engine.recommend_by_document(
            "UW04"
        )

        self.assertTrue(results)

        for item in results:

            self.assertGreaterEqual(
                item.similarity,
                DEFAULT_MIN_SIMILARITY,
            )

    def test_custom_threshold(self):
        results = self.engine.recommend_by_document(
            "UW04",
            min_similarity=0.78,
        )

        self.assertEqual(
            [
                item.document.doc_id
                for item in results
            ],
            ["UW05"],
        )

    def test_top_k(self):
        results = self.engine.recommend_by_document(
            "UW04",
            top_k=1,
        )

        self.assertEqual(
            len(results), 1
        )

    def test_out_of_scope_queries(self):
        queries = (
            "What is the price of Bitcoin?",
            "What is the capital of France?",
            "How can I repair a car engine?",
            "What is the weather forecast for Tokyo?",
            "xyzunknownterm123",
        )

        for query in queries:

            with self.subTest(query=query):

                self.assertEqual(
                    self.engine.recommend_by_query(
                        query
                    ),
                    [],
                )

    def test_empty_queries(self):
        for query in ("", " ", "\n\t"):

            with self.subTest(query=query):

                self.assertEqual(
                    self.engine.recommend_by_query(
                        query
                    ),
                    [],
                )

    def test_unknown_document(self):
        with self.assertRaises(ValueError):

            self.engine.recommend_by_document(
                "UW99"
            )

    def test_invalid_parameters(self):
        for limit in (0, -1, True, 1.5):

            with self.subTest(top_k=limit):

                with self.assertRaises(ValueError):

                    self.engine.recommend_by_query(
                        "design ideas",
                        top_k=limit,
                    )

        for threshold in (
            -0.1,
            1.1,
            float("nan"),
            float("inf"),
        ):

            with self.subTest(
                threshold=threshold
            ):

                with self.assertRaises(ValueError):

                    self.engine.recommend_by_query(
                        "design ideas",
                        min_similarity=threshold,
                    )

    def test_recommendation_explanations(self):
        results = self.engine.recommend_by_document(
            "UW04"
        )

        self.assertTrue(results)

        for item in results:

            self.assertIn(
                MODEL_NAME,
                item.explanation,
            )

            self.assertIn(
                "semantic",
                item.explanation.lower(),
            )

            self.assertIsInstance(
                item.shared_terms,
                tuple,
            )

    def test_semantic_results_without_lexical_overlap(self):
        results = self.engine.recommend_by_query(
            "How can we validate an early design before building it?"
        )

        by_id = {
            item.document.doc_id: item
            for item in results
        }

        self.assertIn(
            "UW06",
            by_id,
        )

        self.assertEqual(
            by_id["UW06"].shared_terms,
            (),
        )

        self.assertGreaterEqual(
            by_id["UW06"].similarity,
            DEFAULT_MIN_SIMILARITY,
        )


if __name__ == "__main__":
    unittest.main()