"""Extractive document-based chatbot for Umbral Web."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sklearn.metrics.pairwise import cosine_similarity

if __package__:
    from .classifier import Document
    from .retrieval import RetrievalEngine
else:
    from classifier import Document
    from retrieval import RetrievalEngine


@dataclass(frozen=True)
class AnswerSource:
    """A document supporting a chatbot answer."""

    document_id: str
    title: str
    category: str
    similarity: float


@dataclass(frozen=True)
class AnswerFragment:
    """An original sentence extracted from a document."""

    document_id: str
    text: str
    position: int
    similarity: float


@dataclass(frozen=True)
class ChatbotResponse:
    """Structured chatbot response."""

    question: str
    answer: str
    sources: tuple[AnswerSource, ...]
    fragments: tuple[AnswerFragment, ...]
    answered: bool


class DocumentChatbot:
    """Retrieve and extract answers from internal documents."""

    NO_ANSWER = (
        "I could not find enough relevant information "
        "in the Umbral Web document collection "
        "to answer this question."
    )

    QUESTION_TERMS = {
        "what", "which", "who", "when", "where",
        "why", "how", "should", "could", "would",
        "can", "does", "did", "please", "tell",
        "explain", "describe", "information",
        "know", "give",
    }

    INTENT_CUES = {
        "lessons": {
            "lesson", "lessons", "learned",
            "future", "conclusion", "agreed",
        },
        "changes": {
            "changed", "changes", "adjusted",
            "shortened", "added", "modified",
            "simplified", "replaced", "reserved",
        },
        "procedure": {
            "first", "then", "before", "after",
            "begins", "must", "each", "ends",
            "prepared", "decides",
        },
        "reason": {
            "because", "if", "helps", "help",
            "intention", "makes", "avoid",
            "clarifies", "difficult",
        },
    }

    def __init__(
        self,
        retrieval_engine: RetrievalEngine | None = None,
    ) -> None:

        self.retrieval = (
            retrieval_engine
            if retrieval_engine is not None
            else RetrievalEngine()
        )

        self.sentences = {}
        self.sentence_matrices = {}
        self.title_terms = {}
        self.document_terms = {}

        self.analyzer = (
            self.retrieval.vectorizer.build_analyzer()
        )

        self.known_terms = set()

        for document in self.retrieval.documents:

            document_id = document.doc_id

            sentences = self._split_sentences(
                document.text
            )

            self.sentences[document_id] = sentences

            if sentences:

                self.sentence_matrices[document_id] = (
                    self.retrieval.vectorizer.transform(
                        sentences
                    )
                )

            title_terms = self._content_terms(
                document.title
            )

            body_terms = self._content_terms(
                document.text
            )

            self.title_terms[document_id] = title_terms

            self.document_terms[document_id] = (
                title_terms | body_terms
            )

            self.known_terms.update(
                self.document_terms[document_id]
            )

        self.title_matrix = (
            self.retrieval.vectorizer.transform(
                [
                    document.title
                    for document in self.retrieval.documents
                ]
            )
        )

    @staticmethod
    def _split_sentences(text: str) -> list[str]:

        normalized = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        if not normalized:
            return []

        return [
            sentence.strip()
            for sentence in re.split(
                r"(?<=[.!?])\s+",
                normalized,
            )
            if sentence.strip()
        ]

    def _content_terms(self, text: str) -> set[str]:

        return {
            term
            for term in self.analyzer(text)
            if " " not in term
            and term not in self.QUESTION_TERMS
        }

    def _query_coverage(
        self,
        query_terms: set[str],
    ) -> tuple[int, float]:

        if not query_terms:
            return 0, 0.0

        matched = query_terms & self.known_terms

        return (
            len(matched),
            len(matched) / len(query_terms),
        )

    @staticmethod
    def _detect_intent(question: str) -> str:

        normalized = question.lower()

        if re.search(
            r"\b(lesson|lessons|learned|takeaway|takeaways)\b",
            normalized,
        ):
            return "lessons"

        if re.search(
            r"\b(change|changes|changed|adjustments|"
            r"improvements|modified)\b",
            normalized,
        ):
            return "changes"

        if re.search(
            r"\bwhy\b",
            normalized,
        ):
            return "reason"

        if re.search(
            r"\b(how|should|steps|procedure|process)\b",
            normalized,
        ):
            return "procedure"

        return "general"

    def _empty_response(
        self,
        question: str,
        message: str | None = None,
    ) -> ChatbotResponse:

        return ChatbotResponse(
            question=question,
            answer=message or self.NO_ANSWER,
            sources=(),
            fragments=(),
            answered=False,
        )

    def _rank_documents(
        self,
        question: str,
        query_vector,
        query_terms: set[str],
        min_document_similarity: float,
    ):

        retrieved = self.retrieval.search(
            question,
            top_k=len(self.retrieval.documents),
        )

        title_scores = cosine_similarity(
            query_vector,
            self.title_matrix,
        )[0]

        index_by_id = {
            document.doc_id: index
            for index, document in enumerate(
                self.retrieval.documents
            )
        }

        candidates = []

        for result in retrieved:

            if result.similarity < min_document_similarity:
                continue

            document_id = result.document.doc_id

            document_terms = self.document_terms[
                document_id
            ]

            title_terms = self.title_terms[
                document_id
            ]

            document_coverage = (
                len(query_terms & document_terms)
                / len(query_terms)
            )

            title_coverage = (
                len(query_terms & title_terms)
                / len(query_terms)
            )

            if document_coverage < 0.35:
                continue

            title_similarity = float(
                title_scores[index_by_id[document_id]]
            )

            ranking_score = (
                0.40 * result.similarity
                + 0.25 * title_similarity
                + 0.20 * document_coverage
                + 0.15 * title_coverage
            )

            candidates.append(
                (
                    ranking_score,
                    result,
                )
            )

        candidates.sort(
            key=lambda item: (
                -item[0],
                -item[1].similarity,
                item[1].document.doc_id,
            )
        )

        return [
            result
            for _, result in candidates
        ]

    def _select_fragments(
        self,
        document: Document,
        query_vector,
        intent: str,
        max_sentences: int,
        min_sentence_similarity: float,
    ) -> list[AnswerFragment]:

        document_id = document.doc_id

        sentences = self.sentences.get(
            document_id,
            [],
        )

        if not sentences:
            return []

        matrix = self.sentence_matrices[
            document_id
        ]

        scores = cosine_similarity(
            query_vector,
            matrix,
        )[0]

        eligible = [
            position
            for position, score in enumerate(scores)
            if score > 0
            and score >= min_sentence_similarity
        ]

        if not eligible:
            return []

        cues = self.INTENT_CUES.get(
            intent,
            set(),
        )

        adjusted_scores = []

        for position, sentence in enumerate(sentences):

            sentence_words = set(
                re.findall(
                    r"\b\w+\b",
                    sentence.lower(),
                )
            )

            cue_count = len(
                sentence_words & cues
            )

            intent_bonus = (
                0.08 * min(cue_count, 3)
            )

            adjusted_scores.append(
                float(scores[position])
                + intent_bonus
            )

        window_size = min(
            max_sentences,
            len(sentences),
        )

        best_start = None
        best_score = -1.0

        for start in range(
            len(sentences) - window_size + 1
        ):

            end = start + window_size

            if not any(
                start <= position < end
                for position in eligible
            ):
                continue

            window_score = sum(
                adjusted_scores[start:end]
            )

            if window_score > best_score:

                best_start = start
                best_score = window_score

        if best_start is None:
            return []

        return [
            AnswerFragment(
                document_id=document_id,
                text=sentences[position],
                position=position,
                similarity=float(scores[position]),
            )
            for position in range(
                best_start,
                best_start + window_size,
            )
        ]

    def ask(
        self,
        question: str,
        max_documents: int = 1,
        max_sentences: int = 7,
        min_document_similarity: float = 0.03,
        min_sentence_similarity: float = 0.05,
        min_query_coverage: float = 0.50,
        min_matched_terms: int = 2,
    ) -> ChatbotResponse:
        """Return a grounded extractive answer."""

        if max_documents < 1:
            raise ValueError(
                "max_documents must be greater than zero."
            )

        if max_sentences < 1:
            raise ValueError(
                "max_sentences must be greater than zero."
            )

        if min_matched_terms < 1:
            raise ValueError(
                "min_matched_terms must be greater than zero."
            )

        for threshold in (
            min_document_similarity,
            min_sentence_similarity,
            min_query_coverage,
        ):

            if not 0.0 <= threshold <= 1.0:
                raise ValueError(
                    "Thresholds must be between 0 and 1."
                )

        question = question.strip()

        if not question:

            return self._empty_response(
                question,
                "Please enter a question.",
            )

        query_terms = self._content_terms(
            question
        )

        matched_count, coverage = (
            self._query_coverage(query_terms)
        )

        if matched_count < min_matched_terms:
            return self._empty_response(question)

        if coverage < min_query_coverage:
            return self._empty_response(question)

        query_vector = (
            self.retrieval.vectorizer.transform(
                [question]
            )
        )

        if query_vector.nnz == 0:
            return self._empty_response(question)

        intent = self._detect_intent(
            question
        )

        candidates = self._rank_documents(
            question,
            query_vector,
            query_terms,
            min_document_similarity,
        )

        sources = []
        all_fragments = []
        answer_sections = []

        remaining_sentences = max_sentences

        for result in candidates:

            if len(sources) >= max_documents:
                break

            if remaining_sentences <= 0:
                break

            document = result.document

            remaining_documents = (
                max_documents - len(sources)
            )

            sentence_budget = max(
                1,
                remaining_sentences // remaining_documents,
            )

            selected = self._select_fragments(
                document=document,
                query_vector=query_vector,
                intent=intent,
                max_sentences=sentence_budget,
                min_sentence_similarity=min_sentence_similarity,
            )

            if not selected:
                continue

            sources.append(
                AnswerSource(
                    document_id=document.doc_id,
                    title=document.title,
                    category=document.category,
                    similarity=result.similarity,
                )
            )

            all_fragments.extend(selected)

            remaining_sentences -= len(selected)

            extracted_text = " ".join(
                fragment.text
                for fragment in selected
            )

            answer_sections.append(
                f"According to {document.title} "
                f"({document.doc_id}):\n"
                f"{extracted_text}"
            )

        if not sources:
            return self._empty_response(question)

        return ChatbotResponse(
            question=question,
            answer="\n\n".join(answer_sections),
            sources=tuple(sources),
            fragments=tuple(all_fragments),
            answered=True,
        )