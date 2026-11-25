"""Automated tests for the Umbral Web document chatbot."""

import unittest

from src.chatbot import DocumentChatbot
from src.retrieval import RetrievalEngine


class TestDocumentChatbot(unittest.TestCase):

    POSITIVE_CASES = (
        (
            "How can we organize a session to generate design ideas?",
            "UW04",
        ),
        (
            "What should we review to prevent animations "
            "from making navigation difficult?",
            "UW08",
        ),
        (
            "What lessons were learned from the Aula Clara course catalog?",
            "UW07",
        ),
        (
            "How should the team test a visual proposal before development?",
            "UW05",
        ),
        (
            "What changes were made to the Estudio Norte portfolio?",
            "UW08",
        ),
        (
            "Why should a content-heavy page have "
            "a recognizable reading order?",
            "UW01",
        ),
        (
            "How can reusable components support a flexible visual identity?",
            "UW03",
        ),
        (
            "How should the group review concepts before choosing a direction?",
            "UW06",
        ),
        (
            "What improvements were made to the Mesa Abierta digital menu?",
            "UW09",
        ),
        (
            "Why should animations be tied to a specific function?",
            "UW02",
        ),
    )

    OUT_OF_SCOPE_CASES = (
        "What is the capital of France?",
        "What is the price of Bitcoin?",
        "xyzunknownterm123",
        "How can I repair a car engine?",
        "What is the weather forecast for Tokyo?",
    )

    @classmethod
    def setUpClass(cls):
        cls.retrieval = RetrievalEngine()
        cls.chatbot = DocumentChatbot(cls.retrieval)

    def test_shared_retrieval_engine(self):
        self.assertIs(
            self.chatbot.retrieval,
            self.retrieval,
        )

    def test_document_collection(self):
        self.assertEqual(
            len(self.chatbot.retrieval.documents),
            9,
        )

        self.assertEqual(
            len(self.chatbot.sentences),
            9,
        )

    def test_positive_questions(self):
        for question, expected_id in self.POSITIVE_CASES:

            with self.subTest(question=question):

                response = self.chatbot.ask(question)

                self.assertTrue(response.answered)
                self.assertTrue(response.answer)
                self.assertEqual(len(response.sources), 1)

                self.assertEqual(
                    response.sources[0].document_id,
                    expected_id,
                )

    def test_all_documents_are_represented(self):
        retrieved_ids = set()

        for question, _ in self.POSITIVE_CASES:

            response = self.chatbot.ask(question)

            retrieved_ids.update(
                source.document_id
                for source in response.sources
            )

        expected_ids = {
            document.doc_id
            for document in self.retrieval.documents
        }

        self.assertEqual(
            retrieved_ids,
            expected_ids,
        )

    def test_out_of_scope_questions(self):
        for question in self.OUT_OF_SCOPE_CASES:

            with self.subTest(question=question):

                response = self.chatbot.ask(question)

                self.assertFalse(response.answered)
                self.assertEqual(response.sources, ())
                self.assertEqual(response.fragments, ())

                self.assertEqual(
                    response.answer,
                    DocumentChatbot.NO_ANSWER,
                )

    def test_empty_questions(self):
        for question in ("", "   "):

            with self.subTest(question=question):

                response = self.chatbot.ask(question)

                self.assertFalse(response.answered)

                self.assertEqual(
                    response.answer,
                    "Please enter a question.",
                )

                self.assertEqual(response.sources, ())
                self.assertEqual(response.fragments, ())

    def test_ideation_answer_content(self):
        response = self.chatbot.ask(
            "How can we organize a session to generate design ideas?"
        )

        expected_phrases = (
            "specific design problem",
            "reviews two references",
            "sketches three alternatives",
            "choosing two directions",
        )

        for phrase in expected_phrases:

            with self.subTest(phrase=phrase):

                self.assertIn(
                    phrase,
                    response.answer.lower(),
                )

    def test_aula_clara_answer_content(self):
        response = self.chatbot.ask(
            "What lessons were learned from the Aula Clara course catalog?"
        )

        self.assertIn(
            "review the content before choosing a template",
            response.answer.lower(),
        )

    def test_visual_proposal_answer_content(self):
        response = self.chatbot.ask(
            "How should the team test a visual proposal before development?"
        )

        expected_phrases = (
            "small test",
            "single-screen prototype",
            "behavior is recorded",
            "continue, adjust, or discard",
        )

        for phrase in expected_phrases:

            with self.subTest(phrase=phrase):

                self.assertIn(
                    phrase,
                    response.answer.lower(),
                )

    def test_estudio_norte_answer_content(self):
        response = self.chatbot.ask(
            "What changes were made to the Estudio Norte portfolio?"
        )

        self.assertIn(
            "transitions were shortened",
            response.answer.lower(),
        )

        self.assertIn(
            "a direct way to open each case study was added",
            response.answer.lower(),
        )

    def test_fragments_are_original(self):
        for question, _ in self.POSITIVE_CASES:

            with self.subTest(question=question):

                response = self.chatbot.ask(question)

                for fragment in response.fragments:

                    original_sentence = self.chatbot.sentences[
                        fragment.document_id
                    ][fragment.position]

                    self.assertEqual(
                        fragment.text,
                        original_sentence,
                    )

                    self.assertIn(
                        fragment.text,
                        response.answer,
                    )

    def test_sources_match_fragments(self):
        for question, _ in self.POSITIVE_CASES:

            with self.subTest(question=question):

                response = self.chatbot.ask(question)

                source_ids = {
                    source.document_id
                    for source in response.sources
                }

                fragment_ids = {
                    fragment.document_id
                    for fragment in response.fragments
                }

                self.assertEqual(
                    source_ids,
                    fragment_ids,
                )

    def test_source_metadata(self):
        documents = {
            document.doc_id: document
            for document in self.retrieval.documents
        }

        for question, _ in self.POSITIVE_CASES:

            response = self.chatbot.ask(question)

            for source in response.sources:

                document = documents[source.document_id]

                self.assertEqual(source.title, document.title)
                self.assertEqual(source.category, document.category)

                self.assertGreater(source.similarity, 0)

                self.assertLessEqual(
                    source.similarity,
                    1.000000001,
                )

    def test_fragments_are_consecutive(self):
        for question, _ in self.POSITIVE_CASES:

            with self.subTest(question=question):

                response = self.chatbot.ask(question)

                positions = [
                    fragment.position
                    for fragment in response.fragments
                ]

                self.assertTrue(positions)

                self.assertEqual(
                    positions,
                    list(
                        range(
                            positions[0],
                            positions[-1] + 1,
                        )
                    ),
                )

    def test_default_sentence_limit(self):
        for question, _ in self.POSITIVE_CASES:

            response = self.chatbot.ask(question)

            self.assertGreater(
                len(response.fragments),
                0,
            )

            self.assertLessEqual(
                len(response.fragments),
                7,
            )

    def test_custom_sentence_limit(self):
        response = self.chatbot.ask(
            "How can we organize a session to generate design ideas?",
            max_sentences=3,
        )

        self.assertTrue(response.answered)

        self.assertLessEqual(
            len(response.fragments),
            3,
        )

    def test_multiple_document_budget(self):
        response = self.chatbot.ask(
            "What should we review to prevent animations "
            "from making navigation difficult?",
            max_documents=2,
            max_sentences=6,
        )

        self.assertTrue(response.answered)

        self.assertLessEqual(
            len(response.sources),
            2,
        )

        self.assertLessEqual(
            len(response.fragments),
            6,
        )

        self.assertEqual(
            len(response.sources),
            len({
                source.document_id
                for source in response.sources
            }),
        )

    def test_high_document_threshold(self):
        response = self.chatbot.ask(
            "How can we organize a session to generate design ideas?",
            min_document_similarity=0.99,
        )

        self.assertFalse(response.answered)
        self.assertEqual(response.sources, ())
        self.assertEqual(response.fragments, ())

    def test_invalid_parameters(self):
        invalid_parameters = (
            {"max_documents": 0},
            {"max_sentences": 0},
            {"min_matched_terms": 0},
            {"min_document_similarity": -0.1},
            {"min_document_similarity": 1.1},
            {"min_sentence_similarity": -0.1},
            {"min_sentence_similarity": 1.1},
            {"min_query_coverage": -0.1},
            {"min_query_coverage": 1.1},
        )

        for parameters in invalid_parameters:

            with self.subTest(parameters=parameters):

                with self.assertRaises(ValueError):

                    self.chatbot.ask(
                        "How can we organize a design session?",
                        **parameters,
                    )

    def test_response_is_reproducible(self):
        question = (
            "What lessons were learned "
            "from the Aula Clara course catalog?"
        )

        first_response = self.chatbot.ask(question)
        second_response = self.chatbot.ask(question)

        self.assertEqual(
            first_response,
            second_response,
        )


if __name__ == "__main__":
    unittest.main()