"""Result interaction coverage for the shared reader and component events."""

import base64
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from prototype_test_support import dispatch, prototype_data

APP = Path(__file__).resolve().parent.parent / "app.py"
IDEATION = "How can we organize a session to generate design ideas?"


class TestToolsWeb(TestCase):
    def setUp(self):
        self.app = AppTest.from_file(str(APP), default_timeout=30).run()
        self.act("navigate", page="Search")
        self.draft = {"query": IDEATION, "limit": 3}

    def act(self, kind, **kwargs):
        dispatch(self.app, kind, **kwargs)
        self.assertFalse(self.app.exception)

    def submit(self):
        self.act("tool_submit", toolDraft=self.draft)

    def test_single_original_and_restore_without_search(self):
        self.submit()
        first = self.app.session_state["document_search_result"]["results"][0].document
        with patch("src.retrieval.RetrievalEngine.search") as search:
            self.act("tool_open", documentId="UW04")
            markup = prototype_data(self.app)["markup"]
            self.assertEqual(markup.count('<article class="archive-reader"'), 1)
            self.assertIn(base64.b64encode(first.path.read_bytes()).decode(), markup)
            self.assertIn("0.200033", markup)
            self.act("tool_open", documentId="UW05")
            markup = prototype_data(self.app)["markup"]
            self.assertEqual(markup.count('<article class="archive-reader"'), 1)
            self.assertIn('data-document-id="UW05"', markup)
            self.act("tool_back")
            self.assertNotIn('<article class="archive-reader"', prototype_data(self.app)["markup"])
            search.assert_not_called()

    def test_search_error_and_retry_preserve_inputs(self):
        with patch("src.retrieval.RetrievalEngine.search", side_effect=OSError("test")):
            self.submit()
        data = prototype_data(self.app)
        self.assertIn('data-status="error"', data["markup"])
        self.assertIn(IDEATION, data["markup"])
        self.assertIsNone(data["tools"]["confirmed"])
        self.submit()
        self.assertEqual(prototype_data(self.app)["tools"]["count"], 3)
