"""P06.4 contract and integration checks for the local graph candidate."""
import base64
import re
import unittest
from dataclasses import replace
from html import unescape
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.retrieval import RetrievalEngine
from src.web.graph_view import RELEASE_SNAPSHOT, load_graph, original_response
from src.web.prototype_ui import _badge, _shell, symbol


class GraphCandidateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = load_graph()
        cls.docs = RetrievalEngine().documents

    def test_snapshot_preserves_pinned_contract(self):
        keys = {node["id"]: node["originalKey"] for node in self.graph["nodes"]}
        self.assertEqual(len(keys), 27)
        self.assertEqual(self.graph["counts"], {"nodes": 27, "edges": 15})
        self.assertIn("project_learnings", keys.values())
        self.assertNotIn("project_lessons", keys.values())
        triples = {(keys[e["source"]], e["verb"], keys[e["target"]]) for e in self.graph["edges"]}
        self.assertIn(("Design and UX", "creates", "Prototype"), triples)
        self.assertIn(("Prototype", "generates", "Reusable Components"), triples)
        self.assertIn(("UW04", "documents_methods_for", "Ideation"), triples)
        self.assertEqual(len(triples), 15)
        self.assertFalse(any(a.startswith("UW") and b.startswith("UW") for a, _, b in triples))

    def test_canonical_ids_use_the_shared_reader_and_exact_download(self):
        ids = {node["documentId"] for node in self.graph["nodes"] if node["documentId"]}
        self.assertEqual(ids, {doc.doc_id for doc in self.docs})
        for document in self.docs:
            with self.subTest(identifier=document.doc_id):
                response = original_response({"id": document.doc_id, "token": "expected"}, self.docs, _badge, symbol)
                self.assertEqual(response["token"], "expected")
                html = response["html"]
                self.assertIn("Back to graph", html)
                encoded, = re.findall(r'href="data:text/plain;base64,([^"]+)"', html)
                original, = re.findall(r'<pre[^>]*>(.*?)</pre>', html, re.S)
                raw = document.path.read_bytes()
                self.assertEqual(base64.b64decode(encoded), raw)
                self.assertEqual(unescape(original), raw.decode("utf-8-sig"))

    def test_missing_original_preserves_return_and_retry(self):
        with TemporaryDirectory() as directory:
            missing = replace(self.docs[0], path=Path(directory) / "missing.txt")
            values = {"id": missing.doc_id, "token": "missing"}
            html = original_response(values, [missing], _badge, symbol)["html"]
            self.assertIn('data-graph-reader="retry"', html)
            self.assertIn('data-graph-reader="back"', html)
            self.assertNotIn("data:text/plain;base64,", html)
        self.assertIsNone(original_response({"id": "UW04"}, self.docs, _badge, symbol))

    def test_feature_switch_preserves_previous_placeholder(self):
        self.assertIn("Integration pending", _shell("Overview", False))
        self.assertIn("Local preview", _shell("Knowledge Graph", False, graph_candidate=True))
        release_markup = _shell("Knowledge Graph", False, graph_candidate=True, graph_release=True)
        self.assertNotIn("Local preview", release_markup)
        self.assertNotIn("Integration pending", release_markup)

    def test_release_rejects_other_bytes_without_using_preview(self):
        self.addCleanup(load_graph.cache_clear)
        with TemporaryDirectory() as directory:
            unrelated = Path(directory) / "unrecognized.json"
            unrelated.write_bytes(RELEASE_SNAPSHOT.read_bytes() + b" ")
            load_graph.cache_clear()
            with patch("src.web.graph_view.RELEASE_SNAPSHOT", unrelated), patch(
                    "src.web.graph_view.PREVIEW_SNAPSHOT", RELEASE_SNAPSHOT):
                with self.assertRaises(ValueError):
                    load_graph(release=True)
                self.assertEqual(load_graph(release=False), self.graph)


if __name__ == "__main__":
    unittest.main()
