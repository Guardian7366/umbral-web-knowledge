"""Automated semantic recommendation web integration tests."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = (
    Path(__file__).resolve().parent.parent
    / "app.py"
)

LEXICAL_METHOD = "Lexical (TF-IDF)"
SEMANTIC_METHOD = "Semantic (BGE)"


class TestSemanticWebIntegration(unittest.TestCase):

    def setUp(self):
        self.app = AppTest.from_file(
            str(APP_PATH),
            default_timeout=120,
        )

        self.app.run()

        self.assert_no_exceptions()

        self.app.radio(
            key="navigation"
        ).set_value(
            "Recommendations"
        ).run()

        self.assert_no_exceptions()

    def assert_no_exceptions(self):
        self.assertEqual(
            len(self.app.exception),
            0,
            str(self.app.exception),
        )

    def select_method(self, method):
        self.app.radio(
            key="recommendation_method"
        ).set_value(method).run()

        self.assert_no_exceptions()

    def select_mode(self, mode):
        self.app.radio(
            key="recommendation_mode"
        ).set_value(mode).run()

        self.assert_no_exceptions()

    def click_recommendations(self):
        button = next(
            button
            for button in self.app.button
            if button.label == "Get recommendations"
        )

        button.click().run()

        self.assert_no_exceptions()

        self.assertEqual(
            len(self.app.error),
            0,
            str(self.app.error),
        )

    def submit_query(self, query):
        self.select_mode("By search query")

        widget = next(
            item
            for item in self.app.text_input
            if item.label == "Search context"
        )

        widget.set_value(query)

        self.click_recommendations()

    def submit_document(
        self,
        document_id,
        threshold=0.55,
    ):
        self.select_mode("By document")

        widget = next(
            item
            for item in self.app.selectbox
            if item.label == "Select a source document"
        )

        widget.set_value(document_id)

        slider = next(
            item
            for item in self.app.slider
            if item.label == "Minimum cosine similarity"
        )

        slider.set_value(threshold)

        self.click_recommendations()

    def get_result(self):
        return self.app.session_state[
            "recommendation_result"
        ]

    def get_result_ids(self):
        return [
            item.document.doc_id
            for item in self.get_result()["results"]
        ]

    def test_default_lexical_method(self):
        self.assertEqual(
            self.app.radio(
                key="recommendation_method"
            ).value,
            LEXICAL_METHOD,
        )

    def test_semantic_default_threshold(self):
        self.select_method(SEMANTIC_METHOD)

        self.assertAlmostEqual(
            self.app.slider(
                key="recommendation_threshold_semantic"
            ).value,
            0.55,
        )

    def test_semantic_query_recommendations(self):
        self.select_method(SEMANTIC_METHOD)

        self.submit_query(
            "How can we brainstorm new concepts as a team?"
        )

        result = self.get_result()

        self.assertEqual(
            result["method"],
            SEMANTIC_METHOD,
        )

        self.assertEqual(
            self.get_result_ids(),
            ["UW04", "UW06", "UW05"],
        )

        captions = [
            item.value
            for item in self.app.caption
        ]

        self.assertIn(
            "Method: Semantic (BGE)",
            captions,
        )

    def test_semantic_document_recommendations(self):
        self.select_method(SEMANTIC_METHOD)

        self.submit_document("UW04")

        self.assertEqual(
            self.get_result_ids(),
            ["UW05", "UW06", "UW03"],
        )

        self.assertNotIn(
            "UW04",
            self.get_result_ids(),
        )

    def test_semantic_custom_threshold(self):
        self.select_method(SEMANTIC_METHOD)

        self.submit_document(
            "UW04",
            threshold=0.78,
        )

        self.assertEqual(
            self.get_result_ids(),
            ["UW05"],
        )

        self.assertAlmostEqual(
            self.get_result()["min_similarity"],
            0.78,
        )

    def test_semantic_out_of_scope_query(self):
        self.select_method(SEMANTIC_METHOD)

        self.submit_query(
            "What is the price of Bitcoin?"
        )

        self.assertEqual(
            self.get_result()["results"],
            [],
        )

        messages = [
            item.value
            for item in self.app.info
        ]

        self.assertTrue(
            any(
                "No relevant recommendations" in message
                for message in messages
            )
        )

    def test_semantic_empty_query(self):
        self.select_method(SEMANTIC_METHOD)

        self.submit_query("")

        self.assertTrue(
            any(
                "Please enter a search query" in item.value
                for item in self.app.warning
            )
        )

    def test_lexical_and_semantic_method_switch(self):
        query = (
            "How can we brainstorm "
            "new concepts as a team?"
        )

        self.select_method(LEXICAL_METHOD)

        self.submit_query(query)

        self.assertEqual(
            self.get_result_ids(),
            ["UW09", "UW08", "UW05"],
        )

        self.select_method(SEMANTIC_METHOD)

        captions = [
            item.value
            for item in self.app.caption
        ]

        self.assertNotIn(
            "Method: Lexical (TF-IDF)",
            captions,
        )

        self.assertFalse(
            any(
                item.value == "Recommended documents"
                for item in self.app.subheader
            )
        )

        self.submit_query(query)

        self.assertEqual(
            self.get_result()["method"],
            SEMANTIC_METHOD,
        )

        self.assertEqual(
            self.get_result_ids(),
            ["UW04", "UW06", "UW05"],
        )


if __name__ == "__main__":
    unittest.main()