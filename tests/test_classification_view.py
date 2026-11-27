from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from prototype_test_support import dispatch, prototype_data
from src.classifier import classify, load_documents, split_documents, train


EXAMPLE = "During the session each designer sketched three alternatives and the team chose two directions to prototype."
APP = Path(__file__).resolve().parents[1] / "app.py"


class TestClassificationSheet(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(str(APP), default_timeout=30).run()
        dispatch(self.app, "navigate", page="Classification")

    def classify(self, text, method="nb", **fields):
        dispatch(self.app, "classify_text", classificationText=text, classificationMethod=method, **fields)
        self.assertFalse(self.app.exception)
        return prototype_data(self.app)["classification"]

    def test_approved_example_matches_actual_models(self):
        training, _ = split_documents(load_documents())
        for method in ("nb", "logreg"):
            vectorizer, classifier = train(training, method)
            categories, _ = classify([EXAMPLE], vectorizer, classifier)
            actual = self.classify(EXAMPLE, method)
            self.assertEqual(actual["result"]["category"], categories[0])
            self.assertEqual(actual["result"]["category"], "creative_methods")

    def test_invalid_input_replaces_result_and_empty_skips_model(self):
        self.assertIsNotNone(self.classify(EXAMPLE)["result"])
        with patch("src.web.classification_view.initialize_classifier") as model:
            data = self.classify("  ")
            model.assert_not_called()
        self.assertIsNone(data["result"])
        self.assertEqual(data["notice"][0], "empty")
        self.assertIsNone(self.classify("xyzunknownterm123")["result"])

    def test_duplicate_revision_does_not_classify_again(self):
        revision = prototype_data(self.app)["revision"]
        self.classify(EXAMPLE, revision=revision)
        with patch("src.web.classification_view.initialize_classifier") as model:
            replayed = self.classify("xyzunknownterm123", revision=revision)
            model.assert_not_called()
        self.assertEqual(replayed["text"], EXAMPLE)
        self.assertEqual(replayed["result"]["category"], "creative_methods")

    def test_technical_failure_keeps_text_and_retry_can_succeed(self):
        with patch("src.web.classification_view.initialize_classifier", side_effect=RuntimeError("test")):
            with self.assertLogs("src.web.classification_view", level="ERROR"):
                data = self.classify(EXAMPLE, "logreg")
        self.assertEqual(data["notice"][0], "error")
        self.assertEqual(data["method"], "logreg")
        self.assertEqual(data["text"], EXAMPLE)
        self.assertEqual(self.classify(EXAMPLE, "logreg")["result"]["category"], "creative_methods")

    def test_navigation_preserves_edited_draft_and_clears_stale_result(self):
        self.classify(EXAMPLE)
        dispatch(self.app, "navigate", page="Overview", classificationText="My edited text", classificationMethod="logreg")
        dispatch(self.app, "navigate", page="Classification")
        data = prototype_data(self.app)["classification"]
        self.assertEqual((data["text"], data["method"]), ("My edited text", "logreg"))
        self.assertIsNone(data["result"])
