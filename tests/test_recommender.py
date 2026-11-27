"""Automated tests for the document recommendation system."""

import unittest

from src.retrieval import RetrievalEngine
from src.recommender import RecommendationEngine


class TestRecommendationEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.retrieval = RetrievalEngine()
        cls.engine = RecommendationEngine(cls.retrieval)

    def test_shared_retrieval_engine(self):
        self.assertIs(
            self.engine.retrieval,
            self.retrieval,
        )

    def test_motion_document_recommendations(self):
        results = self.engine.recommend_by_document("UW02")

        self.assertEqual(
            [result.document.doc_id for result in results],
            ["UW08", "UW01", "UW09"],
        )

        self.assertAlmostEqual(
            results[0].similarity,
            0.073684,
            places=6,
        )

    def test_ideation_document_recommendations(self):
        results = self.engine.recommend_by_document("UW04")

        self.assertEqual(
            [result.document.doc_id for result in results],
            ["UW06", "UW05", "UW02"],
        )

        self.assertAlmostEqual(
            results[0].similarity,
            0.071523,
            places=6,
        )

    def test_aula_clara_document_recommendations(self):
        results = self.engine.recommend_by_document("UW07")

        self.assertEqual(
            [result.document.doc_id for result in results],
            ["UW09", "UW05", "UW01"],
        )

        self.assertAlmostEqual(
            results[0].similarity,
            0.104333,
            places=6,
        )

    def test_source_document_is_excluded(self):
        for document in self.retrieval.documents:

            with self.subTest(document=document.doc_id):

                results = self.engine.recommend_by_document(
                    document.doc_id,
                    top_k=9,
                )

                identifiers = [
                    result.document.doc_id
                    for result in results
                ]

                self.assertNotIn(
                    document.doc_id,
                    identifiers,
                )

    def test_query_ideation_recommendations(self):
        results = self.engine.recommend_by_query(
            "How can we organize a session to generate design ideas?"
        )

        self.assertEqual(
            [result.document.doc_id for result in results],
            ["UW04", "UW05", "UW02"],
        )

        self.assertAlmostEqual(
            results[0].similarity,
            0.200033,
            places=6,
        )

    def test_query_animation_recommendations(self):
        results = self.engine.recommend_by_query(
            "What should we review to prevent animations "
            "from making navigation difficult?"
        )

        self.assertEqual(
            [result.document.doc_id for result in results],
            ["UW08", "UW02", "UW07"],
        )

        self.assertAlmostEqual(
            results[0].similarity,
            0.125356,
            places=6,
        )

    def test_query_aula_clara_recommendations(self):
        results = self.engine.recommend_by_query(
            "What lessons were learned from the Aula Clara course catalog?"
        )

        self.assertEqual(
            [result.document.doc_id for result in results],
            ["UW07"],
        )

        self.assertAlmostEqual(
            results[0].similarity,
            0.232856,
            places=6,
        )

    def test_unknown_document(self):
        with self.assertRaises(ValueError):
            self.engine.recommend_by_document("UW99")

    def test_document_id_normalization(self):
        expected = self.engine.recommend_by_document("UW02")
        actual = self.engine.recommend_by_document(" uw02 ")

        self.assertEqual(
            [result.document.doc_id for result in actual],
            [result.document.doc_id for result in expected],
        )

    def test_empty_query(self):
        self.assertEqual(
            self.engine.recommend_by_query(""),
            [],
        )

        self.assertEqual(
            self.engine.recommend_by_query("   "),
            [],
        )

    def test_unknown_query(self):
        self.assertEqual(
            self.engine.recommend_by_query("xyzunknownterm123"),
            [],
        )

    def test_top_k(self):
        document_results = self.engine.recommend_by_document(
            "UW02",
            top_k=1,
        )

        query_results = self.engine.recommend_by_query(
            "design ideas session",
            top_k=1,
        )

        self.assertEqual(len(document_results), 1)
        self.assertEqual(len(query_results), 1)

    def test_invalid_top_k(self):
        with self.assertRaises(ValueError):
            self.engine.recommend_by_document(
                "UW02",
                top_k=0,
            )

        with self.assertRaises(ValueError):
            self.engine.recommend_by_query(
                "design",
                top_k=0,
            )

    def test_similarity_threshold(self):
        results = self.engine.recommend_by_document(
            "UW02",
            min_similarity=0.06,
        )

        self.assertEqual(
            [result.document.doc_id for result in results],
            ["UW08"],
        )

        self.assertTrue(
            all(result.similarity >= 0.06 for result in results)
        )

    def test_invalid_similarity_threshold(self):
        for threshold in (-0.1, 1.1):

            with self.subTest(threshold=threshold):

                with self.assertRaises(ValueError):
                    self.engine.recommend_by_document(
                        "UW02",
                        min_similarity=threshold,
                    )

                with self.assertRaises(ValueError):
                    self.engine.recommend_by_query(
                        "design",
                        min_similarity=threshold,
                    )

    def test_no_results_above_threshold(self):
        self.assertEqual(
            self.engine.recommend_by_document(
                "UW02",
                min_similarity=0.99,
            ),
            [],
        )

    def test_similarity_order(self):
        results = self.engine.recommend_by_document("UW07")

        scores = [
            result.similarity
            for result in results
        ]

        self.assertGreater(len(scores), 0)

        self.assertEqual(
            scores,
            sorted(scores, reverse=True),
        )

        self.assertTrue(
            all(0 < score <= 1.000000001 for score in scores)
        )

    def test_recommendation_explanations(self):
        results = self.engine.recommend_by_document("UW02")

        self.assertGreater(len(results), 0)

        for result in results:

            self.assertTrue(result.explanation)
            self.assertTrue(result.shared_terms)

            self.assertLessEqual(
                len(result.shared_terms),
                5,
            )

            self.assertIn(
                "UW02",
                result.explanation,
            )

            for term in result.shared_terms:

                self.assertIn(
                    term,
                    result.explanation,
                )

    def test_shared_terms_are_supported_by_vectors(self):
        results = self.engine.recommend_by_document("UW02")

        source_index = self.engine.document_indices["UW02"]

        source_vector = self.retrieval.document_matrix[
            source_index
        ]

        for result in results:

            target_index = self.engine.document_indices[
                result.document.doc_id
            ]

            target_vector = self.retrieval.document_matrix[
                target_index
            ]

            for term in result.shared_terms:

                feature_index = self.retrieval.vectorizer.vocabulary_[
                    term
                ]

                self.assertGreater(
                    source_vector[0, feature_index],
                    0,
                )

                self.assertGreater(
                    target_vector[0, feature_index],
                    0,
                )


if __name__ == "__main__":
    unittest.main()