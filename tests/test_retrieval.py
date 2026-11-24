"""Regression tests for the shared retrieval engine."""

import unittest

from src.retrieval import RetrievalEngine


class TestRetrievalEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = RetrievalEngine()

    def test_document_collection(self):
        self.assertEqual(len(self.engine.documents), 9)

    def test_ideation_query(self):
        results = self.engine.search(
            "How can we organize a session to generate design ideas?"
        )

        self.assertEqual(
            [result.document.doc_id for result in results],
            ["UW04", "UW05", "UW02"],
        )

        self.assertAlmostEqual(
            results[0].similarity,
            0.20003280754534233,
            places=6,
        )

    def test_animation_query(self):
        results = self.engine.search(
            "What should we review to prevent animations "
            "from making navigation difficult?"
        )

        self.assertEqual(
            [result.document.doc_id for result in results],
            ["UW08", "UW02", "UW07"],
        )

        self.assertAlmostEqual(
            results[0].similarity,
            0.1253562652868978,
            places=6,
        )

    def test_aula_clara_query(self):
        results = self.engine.search(
            "What lessons were learned from the Aula Clara course catalog?"
        )

        self.assertEqual(
            [result.document.doc_id for result in results],
            ["UW07"],
        )

        self.assertAlmostEqual(
            results[0].similarity,
            0.23285582980678177,
            places=6,
        )

    def test_empty_query(self):
        self.assertEqual(self.engine.search(""), [])
        self.assertEqual(self.engine.search("   "), [])

    def test_unknown_query(self):
        self.assertEqual(
            self.engine.search("xyzunknownterm123"),
            [],
        )

    def test_top_k(self):
        results = self.engine.search(
            "design ideas session",
            top_k=1,
        )

        self.assertEqual(len(results), 1)

    def test_invalid_top_k(self):
        with self.assertRaises(ValueError):
            self.engine.search("design", top_k=0)

    def test_similarity_order(self):
        results = self.engine.search("design project review")

        scores = [result.similarity for result in results]

        self.assertGreater(len(scores), 0)
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(
            all(0 < score <= 1.000000001 for score in scores)
        )


if __name__ == "__main__":
    unittest.main()