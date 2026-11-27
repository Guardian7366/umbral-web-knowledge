"""Local mascot contract and its bridge to real Assistant turns."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from src.chatbot import DocumentChatbot
from src.retrieval import RetrievalEngine
from src.web.chatbot_view import HISTORY_KEY, REVISION_KEY, _answer, handle_action
from src.web.umbrely_view import ASSETS, JOB, local_manifest, operation_event, schedule_answer, validate_manifest


class UmbrelyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chatbot = DocumentChatbot(RetrievalEngine())

    def setUp(self):
        self.state = {"navigation": "Assistant", REVISION_KEY: "start", HISTORY_KEY: []}

    def dispatch(self, **event):
        handle_action(self.state, {**event, "revision": self.state[REVISION_KEY]}, self.chatbot,
                      answer_question=lambda _engine, q, reply: schedule_answer(self.state, q, reply))

    def finish(self, chatbot=None):
        _answer(chatbot or self.chatbot, *self.state.pop(JOB))
        return operation_event(self.state)

    def test_real_answer_and_abstention_expose_distinct_phases(self):
        self.dispatch(kind="submit", text="How can we organize a session to generate design ideas?")
        event = operation_event(self.state)
        self.assertEqual(event["phase"], "processing")
        self.assertEqual(self.finish(), {**event, "phase": "answerFound"})
        self.assertEqual(self.state[HISTORY_KEY][-1]["response"].sources[0].document_id, "UW04")
        self.dispatch(kind="submit", text="What is the capital of France?")
        self.assertEqual(self.finish()["phase"], "insufficientInformation")
        self.assertFalse(self.state[HISTORY_KEY][-1]["response"].answered)

    def test_recoverable_error_and_retry_use_new_attempt_id(self):
        self.dispatch(kind="submit", text="How can we organize a session to generate design ideas?")
        with patch.object(self.chatbot, "ask", side_effect=OSError("test retrieval failure")):
            error = self.finish()
        self.assertEqual(error["phase"], "recoverableError")
        self.dispatch(kind="retry", turn=0)
        answer = self.finish()
        self.assertNotEqual(error["id"], answer["id"])
        self.assertEqual(answer["phase"], "answerFound")
        self.assertEqual(answer["turn"], error["turn"])

    def test_duplicate_revisions_empty_input_and_clear(self):
        self.dispatch(kind="submit", text="  ")
        self.assertIsNone(operation_event(self.state))
        self.dispatch(kind="submit", text="What is the capital of France?")
        handle_action(self.state, {"revision": "start", "kind": "submit", "text": "Existing action"}, self.chatbot)
        self.assertEqual(len(self.state[HISTORY_KEY]), 2)
        self.finish()
        self.dispatch(kind="clear")
        self.assertIsNone(operation_event(self.state))
        self.assertEqual(self.state[HISTORY_KEY], [])

    def test_disabled_flag_and_missing_assets_fall_back(self):
        with patch.dict("os.environ", {"UMBRAL_UMBRELY_LOCAL": "0"}):
            self.assertIsNone(local_manifest())
        with patch("src.web.umbrely_view.ASSETS", Path(__file__).with_name("missing-local-assets")):
            with patch.dict("os.environ", {"UMBRAL_UMBRELY_LOCAL": "1"}):
                self.assertIsNone(local_manifest())

    @unittest.skipUnless((ASSETS / "umbrely-manifest.json").is_file(), "Local review assets are optional")
    def test_installed_manifest_and_assets(self):
        manifest = json.loads((ASSETS / "umbrely-manifest.json").read_text(encoding="utf-8"))
        validate_manifest(manifest)
        total = 0
        for asset in manifest["assets"].values():
            raw = (ASSETS / asset["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), asset["sha256"])
            self.assertEqual(len(raw), asset["bytes"])
            total += len(raw)
        self.assertEqual(total, 5412)
        self.assertEqual(manifest["assets"]["neutral"]["bytes"], 542)
        invalid = copy.deepcopy(manifest)
        invalid["states"]["sourceDiscovered"]["frames"][0]["tile"] = 64
        with self.assertRaises(ValueError):
            validate_manifest(invalid)
