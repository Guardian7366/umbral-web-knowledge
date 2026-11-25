"""Automated web integration tests for Umbral Web."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = (
    Path(__file__).resolve().parent.parent / "app.py"
)


class TestWebIntegration(unittest.TestCase):

    def setUp(self):
        self.app = AppTest.from_file(
            str(APP_PATH),
            default_timeout=30,
        )

        self.app.run()
        self.assert_no_exceptions()

    def assert_no_exceptions(self):
        self.assertEqual(
            len(self.app.exception),
            0,
            str(self.app.exception),
        )

    def navigate(self, page):
        self.app.radio(
            key="navigation"
        ).set_value(page).run()

        self.assert_no_exceptions()

    def click_button(self, label):
        button = next(
            button
            for button in self.app.button
            if button.label == label
        )

        button.click().run()
        self.assert_no_exceptions()

    def select_option(self, label, value):
        widget = next(
            widget
            for widget in self.app.selectbox
            if widget.label == label
        )

        widget.set_value(value)

    def submit_classification(self, text, algorithm):
        self.navigate("Classification")

        self.select_option(
            "Classification algorithm",
            algorithm,
        )

        self.app.text_area[0].set_value(text)

        self.click_button("Classify document")

    def submit_search(self, query):
        self.navigate("Search")

        self.app.text_input[0].set_value(query)

        self.click_button("Search documents")

    def submit_document_recommendation(
        self,
        document_id,
        threshold=0.0,
    ):
        self.navigate("Recommendations")

        self.app.radio(
            key="recommendation_mode"
        ).set_value("By document").run()

        self.assert_no_exceptions()

        self.select_option(
            "Select a source document",
            document_id,
        )

        slider = next(
            slider
            for slider in self.app.slider
            if slider.label == "Minimum cosine similarity"
        )

        slider.set_value(threshold)

        self.click_button("Get recommendations")

    def submit_query_recommendation(self, query):
        self.navigate("Recommendations")

        self.app.radio(
            key="recommendation_mode"
        ).set_value("By search query").run()

        self.assert_no_exceptions()

        self.app.text_input[0].set_value(query)

        self.click_button("Get recommendations")

    def submit_question(self, question):
        self.app.chat_input[0].set_value(
            question
        ).run()

        self.assert_no_exceptions()

    def test_overview_metrics(self):
        expected_metrics = [
            ("Documents", "9"),
            ("Knowledge categories", "3"),
            ("Validated engine tests (F03)", "49"),
            ("Documents", "3"),
            ("Documents", "3"),
            ("Documents", "3"),
        ]

        actual_metrics = [
            (metric.label, str(metric.value))
            for metric in self.app.metric
        ]

        self.assertCountEqual(
            actual_metrics,
            expected_metrics,
        )

    def test_all_navigation_pages(self):
        pages = (
            "Overview",
            "Documents",
            "Classification",
            "Search",
            "Recommendations",
            "Assistant",
            "Knowledge Graph",
        )

        for page in pages:
            with self.subTest(page=page):
                self.navigate(page)
                self.assertTrue(self.app.title)

    def test_overview_navigation_button(self):
        self.click_button("Open Documents")

        self.assertEqual(
            self.app.radio(
                key="navigation"
            ).value,
            "Documents",
        )

    def test_document_library(self):
        self.navigate("Documents")

        self.assertEqual(
            len(self.app.expander),
            9,
        )

    def test_document_category_filters(self):
        self.navigate("Documents")

        expected_categories = {
            "design_references": [
                "UW01", "UW02", "UW03"
            ],
            "creative_methods": [
                "UW04", "UW05", "UW06"
            ],
            "project_lessons": [
                "UW07", "UW08", "UW09"
            ],
        }

        for category, identifiers in (
            expected_categories.items()
        ):
            with self.subTest(category=category):

                self.app.selectbox(
                    key="library_category"
                ).set_value(category).run()

                self.assert_no_exceptions()

                actual = [
                    item.label.split()[0]
                    for item in self.app.expander
                ]

                self.assertEqual(
                    actual,
                    identifiers,
                )

    def test_document_library_search(self):
        self.navigate("Documents")

        self.app.text_input(
            key="library_query"
        ).set_value("UW04").run()

        self.assert_no_exceptions()

        self.assertEqual(
            len(self.app.expander),
            1,
        )

        self.assertIn(
            "UW04",
            self.app.expander[0].label,
        )

    def test_document_library_no_results(self):
        self.navigate("Documents")

        self.app.text_input(
            key="library_query"
        ).set_value("xyzunknownterm123").run()

        self.assert_no_exceptions()

        self.assertEqual(
            len(self.app.expander),
            0,
        )

        self.assertTrue(self.app.info)

    def test_naive_bayes_classification(self):
        self.submit_classification(
            "Visual hierarchy, typography, modular "
            "composition, and spacing rules help "
            "maintain a consistent visual identity "
            "across interface layouts.",
            "nb",
        )

        result = self.app.session_state[
            "classification_result"
        ]

        self.assertEqual(
            result["category"],
            "design_references",
        )

        self.assertEqual(
            result["training_count"],
            6,
        )

        self.assertEqual(
            result["test_count"],
            3,
        )

    def test_logistic_regression_classification(self):
        cases = (
            (
                "Visual hierarchy, typography, modular "
                "composition, and spacing rules help "
                "maintain a consistent visual identity "
                "across interface layouts.",
                "design_references",
            ),
            (
                "The group reviews references, sketches "
                "alternatives, tests a prototype, and "
                "evaluates different creative directions "
                "before selecting a proposal.",
                "creative_methods",
            ),
            (
                "The project closeout recorded the "
                "adjustments made after the internal "
                "review, the feedback received, and "
                "the lessons learned for future projects.",
                "project_lessons",
            ),
        )

        for text, expected in cases:
            with self.subTest(category=expected):

                self.submit_classification(
                    text,
                    "logreg",
                )

                result = self.app.session_state[
                    "classification_result"
                ]

                self.assertEqual(
                    result["algorithm"],
                    "Logistic Regression",
                )

                self.assertEqual(
                    result["category"],
                    expected,
                )

    def test_empty_classification(self):
        self.submit_classification("", "nb")

        self.assertTrue(self.app.warning)

    def test_unknown_classification_vocabulary(self):
        self.submit_classification(
            "xyzunknownterm123",
            "nb",
        )

        self.assertTrue(self.app.warning)

    def test_search_baseline(self):
        self.submit_search(
            "How can we organize a session "
            "to generate design ideas?"
        )

        result = self.app.session_state[
            "document_search_result"
        ]

        identifiers = [
            item.document.doc_id
            for item in result["results"]
        ]

        self.assertEqual(
            identifiers,
            ["UW04", "UW05", "UW02"],
        )

        self.assertAlmostEqual(
            result["results"][0].similarity,
            0.200033,
            places=6,
        )

    def test_empty_search(self):
        self.submit_search("")

        self.assertTrue(self.app.warning)

    def test_unknown_search(self):
        self.submit_search(
            "xyzunknownterm123"
        )

        result = self.app.session_state[
            "document_search_result"
        ]

        self.assertEqual(
            result["results"],
            [],
        )

    def test_document_recommendations(self):
        self.submit_document_recommendation(
            "UW02"
        )

        result = self.app.session_state[
            "recommendation_result"
        ]

        identifiers = [
            item.document.doc_id
            for item in result["results"]
        ]

        self.assertEqual(
            identifiers,
            ["UW08", "UW01", "UW09"],
        )

        self.assertNotIn(
            "UW02",
            identifiers,
        )

        self.assertTrue(
            result["results"][0].shared_terms
        )

    def test_recommendation_threshold(self):
        self.submit_document_recommendation(
            "UW02",
            threshold=0.06,
        )

        result = self.app.session_state[
            "recommendation_result"
        ]

        self.assertEqual(
            [
                item.document.doc_id
                for item in result["results"]
            ],
            ["UW08"],
        )

    def test_query_recommendations(self):
        self.submit_query_recommendation(
            "What lessons were learned "
            "from the Aula Clara course catalog?"
        )

        result = self.app.session_state[
            "recommendation_result"
        ]

        self.assertEqual(
            [
                item.document.doc_id
                for item in result["results"]
            ],
            ["UW07"],
        )

    def test_empty_recommendation_query(self):
        self.submit_query_recommendation("")

        self.assertTrue(self.app.warning)

    def test_unknown_recommendation_query(self):
        self.submit_query_recommendation(
            "xyzunknownterm123"
        )

        result = self.app.session_state[
            "recommendation_result"
        ]

        self.assertEqual(
            result["results"],
            [],
        )

    def test_chatbot_example_question(self):
        self.navigate("Assistant")

        self.click_button(
            "How can we organize a session "
            "to generate design ideas?"
        )

        history = self.app.session_state[
            "assistant_history"
        ]

        self.assertEqual(len(history), 2)

        response = history[1]["response"]

        self.assertTrue(response.answered)

        self.assertEqual(
            response.sources[0].document_id,
            "UW04",
        )

    def test_chatbot_abstention(self):
        self.navigate("Assistant")

        self.submit_question(
            "What is the price of Bitcoin?"
        )

        history = self.app.session_state[
            "assistant_history"
        ]

        response = history[1]["response"]

        self.assertFalse(response.answered)
        self.assertEqual(response.sources, ())

    def test_chatbot_history_and_clear(self):
        self.navigate("Assistant")

        self.submit_question(
            "What lessons were learned "
            "from the Aula Clara course catalog?"
        )

        self.submit_question(
            "What is the price of Bitcoin?"
        )

        self.assertEqual(
            len(
                self.app.session_state[
                    "assistant_history"
                ]
            ),
            4,
        )

        self.navigate("Documents")
        self.navigate("Assistant")

        self.assertEqual(
            len(
                self.app.session_state[
                    "assistant_history"
                ]
            ),
            4,
        )

        self.click_button(
            "Clear conversation"
        )

        self.assertEqual(
            self.app.session_state[
                "assistant_history"
            ],
            [],
        )


if __name__ == "__main__":
    unittest.main()