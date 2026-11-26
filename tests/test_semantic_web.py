"""Automated semantic recommendation web integration tests."""

import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from prototype_test_support import dispatch, prototype_data

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"
SEMANTIC_METHOD = "Semantic (BGE)"


class TestSemanticWebIntegration(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(str(APP_PATH), default_timeout=120).run()
        dispatch(self.app, "navigate", page="Recommendations")
        self.assert_no_exceptions()
        self.draft = prototype_data(self.app)["tools"]["defaults"]

    def assert_no_exceptions(self):
        self.assertEqual(len(self.app.exception), 0, str(self.app.exception))

    def submit(self, **changes):
        self.draft = {**self.draft, **changes}
        dispatch(self.app, "tool_submit", toolDraft=self.draft)
        self.assert_no_exceptions()

    def ids(self):
        return [item.document.doc_id for item in self.app.session_state["recommendation_result"]["results"]]

    def test_default_lexical_method(self):
        self.assertEqual(self.draft["method"], "lexical")
        self.assertIn('value="lexical" checked', prototype_data(self.app)["markup"])

    def test_semantic_default_threshold(self):
        self.assertAlmostEqual(self.draft["thresholds"]["semantic"], 0.55)
        self.assertAlmostEqual(self.draft["thresholds"]["lexical"], 0.0)

    def test_semantic_query_recommendations(self):
        self.submit(method="semantic", mode="query", query="How can we brainstorm new concepts as a team?")
        self.assertEqual(self.app.session_state["recommendation_result"]["method"], SEMANTIC_METHOD)
        self.assertEqual(self.ids(), ["UW04", "UW06", "UW05"])
        self.assertIn("Related ideas", prototype_data(self.app)["markup"])
        dispatch(self.app, "tool_inspect", documentId="UW04")
        self.assertIn("BGE · Cosine similarity", prototype_data(self.app)["markup"])

    def test_semantic_document_recommendations(self):
        self.submit(method="semantic", source="UW04")
        self.assertEqual(self.ids(), ["UW05", "UW06", "UW03"])
        self.assertNotIn("UW04", self.ids())

    def test_semantic_custom_threshold(self):
        self.submit(method="semantic", source="UW04", thresholds={"lexical": 0.0, "semantic": 0.78})
        self.assertEqual(self.ids(), ["UW05"])
        self.assertAlmostEqual(self.app.session_state["recommendation_result"]["min_similarity"], 0.78)

    def test_semantic_out_of_scope_query(self):
        self.submit(method="semantic", mode="query", query="What is the price of Bitcoin?")
        self.assertEqual(self.ids(), [])
        self.assertIn("No related documents with these settings.", prototype_data(self.app)["markup"])

    def test_semantic_empty_query(self):
        with patch("src.web.recommendation_view.initialize_semantic_engine") as initialize:
            self.submit(method="semantic", mode="query", query="")
            initialize.assert_not_called()
        self.assertIn("Enter a question.", prototype_data(self.app)["markup"])

    def test_lexical_and_semantic_method_switch(self):
        query = "How can we brainstorm new concepts as a team?"
        self.submit(method="lexical", mode="query", query=query)
        self.assertEqual(self.ids(), ["UW09", "UW08", "UW05"])
        new_draft = {**self.draft, "method": "semantic"}
        with patch("src.web.recommendation_view.initialize_semantic_engine") as initialize:
            dispatch(self.app, "navigate", page="Search", toolDraft=new_draft)
            dispatch(self.app, "navigate", page="Recommendations")
            initialize.assert_not_called()
        data = prototype_data(self.app)["tools"]
        self.assertEqual(data["defaults"]["method"], "semantic")
        self.assertEqual(data["confirmed"]["method"], "lexical")
        self.assertNotEqual(data["defaults"]["method"], data["confirmed"]["method"])
        self.submit(method="semantic")
        self.assertEqual(self.app.session_state["recommendation_result"]["method"], SEMANTIC_METHOD)
        self.assertEqual(self.ids(), ["UW04", "UW06", "UW05"])

    def test_semantic_failure_keeps_draft_and_requires_explicit_retry(self):
        with patch("src.web.recommendation_view.initialize_semantic_engine", side_effect=OSError("test")) as initialize:
            self.submit(method="semantic", source="UW04")
            initialize.assert_called_once()
        data = prototype_data(self.app)
        self.assertIn('data-status="error"', data["markup"])
        self.assertIn("Retry or choose Shared words.", data["markup"])
        self.assertIsNone(data["tools"]["confirmed"])
        self.assertEqual(data["tools"]["defaults"]["source"], "UW04")
        self.submit(method="lexical", source="UW04")
        self.assertEqual(self.app.session_state["recommendation_result"]["method"], "Lexical (TF-IDF)")
