"""Regression tests for the Documents index, reader, and direct navigation."""

import base64
from html import unescape
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from prototype_test_support import dispatch, prototype_data
from src.web.documents_archive import document_payload


REPO = Path(__file__).resolve().parents[1]


class TestDocumentsArchive(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(str(REPO / "app.py"), default_timeout=30).run()

    def event(self, kind, **values):
        dispatch(self.app, kind, **values)
        self.assertFalse(self.app.exception)
        return prototype_data(self.app)

    def test_content_and_title_search_combine_with_category_and_reset(self):
        self.event("navigate", page="Documents")
        for query in (" UW04 ", "idea generation session", "without repeating the entire session"):
            data = self.event("library_query", query=query)
            self.assertEqual(data["archive"]["matchingIds"], ["UW04"])
        data = self.event("library_category", category="project_lessons")
        self.assertEqual(data["archive"]["matchingIds"], [])
        data = self.event("library_clear")
        self.assertEqual(data["archive"]["matchingIds"], ["UW07", "UW08", "UW09"])
        self.assertEqual(len(self.event("library_reset")["archive"]["matchingIds"]), 9)

    def test_single_reader_has_exact_original_and_exact_download(self):
        self.event("navigate", page="Documents")
        self.event("library_group", category="creative_methods")
        for identifier in ("UW04", "UW05"):
            data = self.event("library_open", id=identifier)
            markup = data["markup"]
            raw = (REPO / "data/documents" / f"{identifier.lower()}.txt").read_bytes()
            encoded = re.findall(r'href="data:text/plain;base64,([^"]+)"', markup)
            self.assertEqual(len(encoded), 1)
            self.assertEqual(base64.b64decode(encoded[0]), raw)
            original = re.search(r'<pre class="archive-original"[^>]*>(.*?)</pre>', markup, re.DOTALL)
            self.assertEqual(unescape(original[1]), raw.decode("utf-8-sig"))
            self.assertEqual(markup.count('class="archive-reader"'), 1)

    def test_direct_id_restores_previous_filter_and_duplicate_is_ignored(self):
        self.event("navigate", page="Documents")
        self.event("library_category", category="project_lessons")
        self.event("library_query", query="UW09")
        self.event("navigate", page="Overview")
        revision = prototype_data(self.app)["revision"]
        data = self.event("open_document", revision=revision, id="UW04")
        self.assertEqual(data["page"], "Documents")
        self.assertEqual(data["archive"]["group"], "creative_methods")
        self.assertEqual(data["archive"]["selected"], "UW04")
        self.assertTrue(data["archive"]["reading"])
        self.assertFalse(data["archive"]["opening"])
        self.event("library_back", id="UW04")
        data = self.event("open_document", revision=revision, id="UW04")
        self.assertFalse(data["archive"]["reading"])
        self.assertIn("Restore previous filters", data["markup"])
        data = self.event("library_restore")
        self.assertEqual(data["archive"]["matchingIds"], ["UW09"])
        self.assertEqual(self.event("library_origin")["page"], "Overview")

    def test_first_opening_is_once_per_session_and_unknown_id_is_reported(self):
        data = self.event("navigate", page="Documents")
        self.assertTrue(data["archive"]["opening"])
        self.app.run()
        self.assertFalse(prototype_data(self.app)["archive"]["opening"])
        self.event("navigate", page="Overview")
        data = self.event("open_document", id="UW999")
        self.assertIn("Document not found.", data["markup"])
        self.assertFalse(data["archive"]["reading"])
        self.assertEqual(len(data["archive"]["matchingIds"]), 9)

    def test_filter_change_closes_an_excluded_original(self):
        self.event("open_document", id="UW04")
        data = self.event("library_category", category="design_references")
        self.assertFalse(data["archive"]["reading"])
        self.assertIn("outside these filters", data["markup"])
        self.assertEqual(data["archive"]["matchingIds"], ["UW01", "UW02", "UW03"])

    def test_missing_original_allows_retry_without_discarding_metadata(self):
        with patch("src.web.documents_archive.document_payload") as load:
            def missing(document):
                with TemporaryDirectory() as folder:
                    from dataclasses import replace
                    return document_payload(replace(document, path=Path(folder) / "missing.txt"))
            load.side_effect = missing
            data = self.event("open_document", id="UW04")
        self.assertTrue(data["archive"]["reading"])
        self.assertIn("The original document is currently unavailable.", data["markup"])
        self.assertIn("Brief Idea Generation Session", data["markup"])
        self.assertNotIn('href="data:text/plain', data["markup"])
        recovered = self.event("library_retry")
        self.assertIn('download="uw04.txt"', recovered["markup"])
