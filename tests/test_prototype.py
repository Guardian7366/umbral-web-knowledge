"""Regression coverage for the vertical prototype and its event bridge."""

import base64
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from prototype_test_support import dispatch, prototype_data
from src.chatbot import DocumentChatbot


REPO = Path(__file__).resolve().parents[1]
C01 = "How can we organize a session to generate design ideas?"
C04 = "How should the team test a visual proposal before development?"
C07 = "What is the capital of France?"


class TestVerticalPrototype(unittest.TestCase):
    def new_app(self):
        return AppTest.from_file(str(REPO / "app.py"), default_timeout=30).run()

    def setUp(self):
        self.app = self.new_app()
        self.assertFalse(self.app.exception)

    def event(self, kind, **fields):
        dispatch(self.app, kind, **fields)
        self.assertFalse(self.app.exception)

    def test_blank_transfer_preserves_history_without_calling_engine(self):
        self.event("submit", text=C01)
        self.event("navigate", page="Overview")
        with patch.object(DocumentChatbot, "ask") as ask:
            self.event("submit", text=" \n   ")
            ask.assert_not_called()
        self.assertEqual(prototype_data(self.app)["page"], "Assistant")
        self.assertEqual(len(self.app.session_state["assistant_history"]), 2)

    def test_replayed_transfer_only_creates_one_turn_and_preserves_inner_text(self):
        question = "How can we organize a session\nto generate design ideas?"
        revision = prototype_data(self.app)["revision"]
        with patch.object(DocumentChatbot, "ask", autospec=True, side_effect=DocumentChatbot.ask) as ask:
            self.event("submit", revision=revision, text=f"  {question}  ")
            self.event("submit", revision=revision, text=f"  {question}  ")
            self.app.run()
            self.event("navigate", page="Overview")
            self.event("navigate", page="Assistant")
            self.assertEqual(ask.call_count, 1)
        history = self.app.session_state["assistant_history"]
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["content"], question)
        self.assertEqual(history[1]["response"].question, question)
        self.event("submit", text=question)
        self.assertEqual(len(self.app.session_state["assistant_history"]), 4)

    def test_real_sources_and_download_payload(self):
        self.event("submit", text=C01)
        self.event("submit", text=C04)
        self.event("submit", text=C07)
        data = prototype_data(self.app)
        evidence = data["evidence"]
        self.assertEqual(set(evidence), {"0-UW04", "1-UW05"})
        self.assertEqual(evidence["0-UW04"]["similarity"], "0.200033")
        self.assertEqual(len(evidence["0-UW04"]["fragments"]), 7)
        path = REPO / "data/documents/uw04.txt"
        self.assertEqual(base64.b64decode(data["documents"]["UW04"]["bytes"]), path.read_bytes())
        self.assertIn("I could not find enough relevant information", data["markup"])

    def test_failed_turn_is_retried_in_place(self):
        with patch.object(DocumentChatbot, "ask", side_effect=RuntimeError("transient test error")):
            with self.assertLogs("src.web.chatbot_view", level="ERROR"):
                self.event("submit", text=C04)
        self.assertEqual(self.app.session_state["assistant_history"][1]["status"], "error")
        self.assertIn("Retry", prototype_data(self.app)["markup"])
        self.event("retry", turn=0)
        history = self.app.session_state["assistant_history"]
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["content"], C04)
        self.assertEqual(history[1]["response"].sources[0].document_id, "UW05")

    def test_each_session_owns_its_history(self):
        self.event("submit", text=C01)
        second = self.new_app()
        self.assertFalse(second.exception)
        self.assertEqual(second.session_state["assistant_history"], [])
        self.assertEqual(prototype_data(second)["page"], "Overview")
        self.event("clear")
        self.assertEqual(self.app.session_state["assistant_history"], [])
