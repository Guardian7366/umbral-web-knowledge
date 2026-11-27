"""Contextual reading recommendations backed by the existing two engines."""

from html import escape
import logging
from uuid import uuid4

import streamlit as st

from src.web.chatbot_view import REVISION_KEY
from src.web.document_views import category_label
from src.web.search_view import (
    feedback, handle_ranking_action, heading, index_heading, limit_control,
    match_details, original_reader, rank_item,
)

LOGGER = logging.getLogger(__name__)
LEXICAL_METHOD = "Lexical (TF-IDF)"
SEMANTIC_METHOD = "Semantic (BGE)"
METHODS = {"lexical": LEXICAL_METHOD, "semantic": SEMANTIC_METHOD}
MODES = {"document": "By document", "query": "By search query"}
DEFAULT_THRESHOLDS = {"lexical": 0.0, "semantic": 0.55}


@st.cache_resource
def initialize_semantic_engine(_retrieval):
    """Load BGE once on demand for the application's fixed collection."""
    from src.semantic_recommender import SemanticRecommendationEngine

    return SemanticRecommendationEngine(_retrieval)


def _view(state, documents):
    return state.setdefault("recommendations_view", {
        "draft": {
            "mode": "document", "method": "lexical", "source": documents[0].doc_id, "query": "",
            "limits": {mode: min(3, len(documents) - (mode == "document")) for mode in MODES},
            "thresholds": DEFAULT_THRESHOLDS.copy(),
        },
    })


def _valid_draft(value, documents):
    if not isinstance(value, dict):
        return False
    mode, method = value.get("mode"), value.get("method")
    limits, thresholds = value.get("limits"), value.get("thresholds")
    return (
        isinstance(mode, str) and mode in MODES
        and isinstance(method, str) and method in METHODS
        and isinstance(value.get("query"), str)
        and any(doc.doc_id == value.get("source") for doc in documents)
        and isinstance(limits, dict) and isinstance(thresholds, dict)
        and all(type(limits.get(key)) is int and 1 <= limits[key] <= len(documents) - (key == "document")
                for key in MODES)
        and all(type(thresholds.get(key)) in (int, float) and 0 <= thresholds[key] <= 1
                for key in METHODS)
    )


def handle_recommendations_action(state, action, recommender):
    """Persist the draft separately from the last explicit recommendation request."""
    kind = action["kind"]
    documents = recommender.retrieval.documents
    tool = _view(state, documents)
    draft = action.get("toolDraft")
    if kind in ("tool_submit", "navigate") and _valid_draft(draft, documents):
        tool["draft"] = {key: draft[key] for key in tool["draft"]}
    if kind == "navigate":
        tool["reading"] = False
        return
    state[REVISION_KEY] = uuid4().hex
    if kind != "tool_submit":
        batch = state.get("recommendation_result")
        if batch:
            handle_ranking_action(tool, action, batch)
        return

    draft = tool["draft"]
    mode, method = draft["mode"], draft["method"]
    query, identifier = draft["query"].strip(), draft["source"]
    limit, threshold = draft["limits"][mode], draft["thresholds"][method]
    tool.update(notice=None, selected=None, expanded=None, reading=False)
    state.pop("recommendation_result", None)
    if mode == "query" and not query:
        tool["notice"] = ("empty", "Enter a question.")
        return

    try:
        engine = initialize_semantic_engine(recommender.retrieval) if method == "semantic" else recommender
        if mode == "document":
            source = next(doc for doc in documents if doc.doc_id == identifier)
            results = engine.recommend_by_document(identifier, top_k=limit, min_similarity=threshold)
            context = f"{identifier} - {source.title}"
        else:
            results = engine.recommend_by_query(query, top_k=limit, min_similarity=threshold)
            context = query
    except Exception:
        LOGGER.exception("Recommendation processing failed")
        message = ("Related ideas is temporarily unavailable. Retry or choose Shared words."
                   if method == "semantic" else "Couldn’t find related documents.")
        tool["notice"] = ("error", message)
        return

    confirmed = {
        "mode": mode, "method": method, "limit": limit, "threshold": threshold,
        "query" if mode == "query" else "source": query if mode == "query" else identifier,
    }
    state["recommendation_result"] = {
        "mode": MODES[mode], "method": METHODS[method], "context": context, "results": results,
        "top_k": limit, "min_similarity": threshold, "confirmed": confirmed,
    }


def _segments(name, legend, options, active):
    inputs = "".join(
        f'<label><input type="radio" name="{name}" value="{key}"'
        f'{" checked" if key == active else ""}><span>{label}</span></label>'
        for key, label in options.items()
    )
    return (f'<fieldset class="tool-segments tool-{name}"><legend>{legend}</legend>'
            f'<div class="classification-options">{inputs}</div></fieldset>')


def _explanation(result, batch, symbol):
    suggested = result.document.doc_id
    confirmed = batch["confirmed"]
    semantic = confirmed["method"] == "semantic"
    label = "BGE" if semantic else "TF-IDF"
    origin = confirmed.get("source", "your question")
    terms = ", ".join(result.shared_terms) or "No shared terms in the collection vocabulary."
    reason = ("This document is close in meaning to the source context." if semantic else
              f"It shares weighted terms with {origin}.")
    term_heading = "<strong>Additional shared words</strong>" if semantic else ""
    description = ("BAAI/bge-small-en-v1.5 uses 384-dimensional contextual embeddings on CPU through "
                   "FastEmbed and ONNX Runtime. Shared words are extra context. Meaning similarity determines the order."
                   if semantic else "TF-IDF compares vectors of weighted words and phrases.")
    detail = match_details(label, result, f"""
        <p>{escape(result.explanation)}</p><p>{description}</p>
        <p>Source: {escape(batch['context'])}</p>
        <p>Maximum results: {batch['top_k']} · Minimum similarity: {batch['min_similarity']:.2f}</p>
        <p>Scores from the two methods use different scales.</p>
    """)
    return f"""
        <div class="tool-explanation" id="tool-explanation-{escape(suggested)}">
            <p>{reason}</p>{term_heading}<p class="tool-terms">{escape(terms)}</p>
            <div class="tool-evidence-actions">
                <button class="text-action" type="button" data-tool-action="tool_open" data-id="{escape(suggested)}">
                    Read original{symbol('next')}
                </button>
                {detail}
            </div>
        </div>
    """


def render_recommendations(state, recommender, badge, symbol):
    documents = recommender.retrieval.documents
    tool = _view(state, documents)
    draft = tool["draft"]
    mode, method = draft["mode"], draft["method"]
    is_query = mode == "query"
    batch = state.get("recommendation_result")
    options = "".join(
        f'<option value="{escape(doc.doc_id)}"{" selected" if doc.doc_id == draft["source"] else ""}>'
        f'{escape(doc.doc_id)} · {escape(doc.title)}</option>'
        for doc in documents
    )
    results, reader, index = [], "", ""
    if batch:
        results = batch["results"]
        rows = "".join(
            rank_item(i, result.document, symbol, result.document.doc_id == tool.get("expanded"),
                      expanded=result.document.doc_id == tool.get("expanded"),
                      panel=_explanation(result, batch, symbol) if result.document.doc_id == tool.get("expanded") else "")
            for i, result in enumerate(results, 1)
        )
        method_label = "Related ideas" if batch["method"] == SEMANTIC_METHOD else "Shared words"
        origin = batch["confirmed"].get("source", batch["context"])
        matches = (f'<ol class="tool-ranking" aria-labelledby="tool-index-title">{rows}</ol>' if rows else
                   '<p class="tool-empty">No related documents with these settings.</p>')
        index = f"""
            <section class="tool-index" aria-labelledby="tool-index-title">
                {index_heading(len(results), 'related document')}
                <p class="tool-confirmed">{method_label} · From {escape(origin)}</p>
                {matches}
            </section>
        """
        if tool.get("reading"):
            selected = next((result for result in results if result.document.doc_id == tool.get("selected")), None)
            if selected:
                reader = original_reader(selected, badge, symbol)

    output = f"""
        <div class="tool-workspace tool-recommendations{' is-reading' if reader else ''}">
            {heading('Recommendations', 'Find connections', 'Start with a document or a question to discover related reading.')}
            <form class="tool-form" autocomplete="off">
                {_segments('mode', 'Start from', {'document': 'A document', 'query': 'A question'}, mode)}
                <div class="tool-source">
                    <div class="tool-source-card" {'hidden' if is_query else ''}>
                        <span class="tool-source-tab">Source document</span>
                        <span class="tool-source-id"></span>
                        <h2></h2><p class="tool-source-category"></p>
                        <label>Choose document<select name="source">{options}</select></label>
                    </div>
                    <label class="tool-context-query" {'' if is_query else 'hidden'}>Your question
                        <textarea rows="2" name="query" aria-describedby="tool-notice">{escape(draft['query'])}</textarea>
                    </label>
                </div>
                {_segments('method', 'Find connections by', {'lexical': 'Shared words', 'semantic': 'Related ideas'}, method)}
                <div class="tool-parameters">
                    {limit_control(draft['limits'][mode], len(documents) - (not is_query))}
                    <details class="tool-settings" id="tool-settings">
                        <summary>Settings</summary>
                        <div class="tool-settings-body"><label>Minimum similarity
                            <input name="threshold" type="number" min="0" max="1" step="0.01" value="{draft['thresholds'][method]:.2f}">
                        </label><p class="tool-threshold-help"></p></div>
                    </details>
                </div>
                <p class="tool-method-help" aria-live="polite"></p>
                <div class="tool-recommend">
                    {feedback(tool, 'Find related documents', 'Finding related documents…')}
                </div>
                <p class="tool-dirty" hidden>Find related documents again to use the edited criteria.</p>
                {index}
                {reader}
                <svg class="tool-connection" aria-hidden="true"><path pathLength="1" /></svg>
            </form>
        </div>
    """
    return output, {
        "confirmed": batch["confirmed"] if batch else None,
        "selected": tool.get("selected"), "count": len(results), "defaults": draft,
        "sources": {doc.doc_id: {"title": doc.title, "category": category_label(doc.category)} for doc in documents},
    }
