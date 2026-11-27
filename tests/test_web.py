"""Automated web integration tests for Umbral Web."""

import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from prototype_test_support import dispatch, prototype_data


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
        dispatch(self.app, "navigate", page=page)

        self.assert_no_exceptions()

    def submit_classification(self, text, algorithm):
        self.navigate("Classification")
        dispatch(self.app, "classify_text", classificationText=text, classificationMethod=algorithm)
        self.assert_no_exceptions()

    def submit_search(self, query):
        self.navigate("Search")

        dispatch(self.app, "tool_submit", toolDraft={"query": query, "limit": 3})
        self.assert_no_exceptions()

    def submit_document_recommendation(self, document_id, threshold=0.0):
        self.submit_recommendation("document", document_id, "", threshold)

    def submit_query_recommendation(self, query):
        self.submit_recommendation("query", "UW01", query, 0.0)

    def submit_recommendation(self, mode, document_id, query, threshold):
        self.navigate("Recommendations")
        dispatch(self.app, "tool_submit", toolDraft={
            "mode": mode, "method": "lexical", "source": document_id, "query": query,
            "limits": {"document": 3, "query": 3},
            "thresholds": {"lexical": threshold, "semantic": 0.55},
        })
        self.assert_no_exceptions()

    def submit_question(self, question):
        dispatch(self.app, "submit", text=question)
        self.assert_no_exceptions()

    def test_overview_metrics(self):
        markup = prototype_data(self.app)["markup"]
        self.assertIn("9 documents", markup)
        self.assertIn("3 categories", markup)
        for category in ("Design references", "Creative methods", "Project lessons"):
            self.assertIn(f"{category} · 3 documents", markup)

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
                data = prototype_data(self.app)
                self.assertEqual(data["page"], page)
                self.assertIn(f'data-route="{page}" aria-current="page"', data["markup"])
                self.assertIn('<h1 id="page-title"', data["markup"])
                if page == "Knowledge Graph":
                    self.assertEqual(data["graph"]["graph"]["counts"], {"nodes": 27, "edges": 15})

    def test_disabled_graph_preserves_native_placeholder(self):
        with patch.dict("os.environ", {"UMBRAL_GRAPH_RELEASE": "0", "UMBRAL_GRAPH_CANDIDATE": "0"}):
            self.navigate("Knowledge Graph")
            self.assertIsNone(prototype_data(self.app)["graph"])
            self.assertEqual(self.app.title[0].value, "Knowledge graph")

    def test_overview_navigation_button(self):
        self.assertIn("Browse documents", prototype_data(self.app)["markup"])
        dispatch(self.app, "navigate", page="Documents")
        self.assert_no_exceptions()
        self.assertEqual(self.app.session_state["navigation"], "Documents")

    def test_document_library(self):
        self.navigate("Documents")
        data = prototype_data(self.app)
        self.assertEqual(len(data["archive"]["matchingIds"]), 9)
        self.assertEqual(data["markup"].count("data-archive-group="), 3)
        self.assertEqual(len(self.app.expander), 0)

    def test_document_category_filters(self):
        self.navigate("Documents")
        expected = {
            "design_references": ["UW01", "UW02", "UW03"],
            "creative_methods": ["UW04", "UW05", "UW06"],
            "project_lessons": ["UW07", "UW08", "UW09"],
        }
        for category, identifiers in expected.items():
            with self.subTest(category=category):
                dispatch(self.app, "library_category", category=category)
                self.assert_no_exceptions()
                data = prototype_data(self.app)
                self.assertEqual(data["archive"]["matchingIds"], identifiers)
                for identifier in identifiers:
                    self.assertIn(f'data-archive-open="{identifier}"', data["markup"])

    def test_document_library_search(self):
        self.navigate("Documents")
        dispatch(self.app, "library_query", query="UW04")
        self.assert_no_exceptions()
        data = prototype_data(self.app)
        self.assertEqual(data["archive"]["matchingIds"], ["UW04"])
        self.assertIn('data-archive-open="UW04"', data["markup"])

    def test_document_library_no_results(self):
        self.navigate("Documents")
        dispatch(self.app, "library_query", query="xyzunknownterm123")
        self.assert_no_exceptions()
        data = prototype_data(self.app)
        self.assertEqual(data["archive"]["matchingIds"], [])
        self.assertIn("No documents match the selected filters.", data["markup"])

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

        self.assertEqual(prototype_data(self.app)["classification"]["notice"][0], "empty")

    def test_unknown_classification_vocabulary(self):
        self.submit_classification(
            "xyzunknownterm123",
            "nb",
        )

        self.assertEqual(prototype_data(self.app)["classification"]["notice"][0], "unknown")

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

        self.assertIn('data-status="empty"', prototype_data(self.app)["markup"])

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

        self.assertIn('data-status="empty"', prototype_data(self.app)["markup"])

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

        suggestions = prototype_data(self.app)["suggestions"]
        self.assertEqual(len(suggestions), 2)
        self.assertEqual(suggestions[0], "How can we organize a session to generate design ideas?")
        self.assertEqual(suggestions[1], "How should the team test a visual proposal before development?")
        self.submit_question(suggestions[0])

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

        self.assertIn("Clear this conversation?", prototype_data(self.app)["markup"])
        dispatch(self.app, "clear")
        self.assert_no_exceptions()

        self.assertEqual(
            self.app.session_state[
                "assistant_history"
            ],
            [],
        )


if __name__ == "__main__":
    unittest.main()