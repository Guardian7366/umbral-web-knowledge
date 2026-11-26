"""Streamlit adapter for the Canto abierto vertical prototype."""

import json
from html import escape
from pathlib import Path
from uuid import uuid4

import streamlit as st

from src.web.chatbot_view import EXAMPLE_QUESTIONS, HISTORY_KEY, PAGES, REVISION_KEY, handle_action
from src.web.classification_view import handle_classification_action, render_classification
from src.web.document_views import category_label
from src.web.documents_archive import (
    document_payload, handle_library_action, remember_library_query, render_archive,
)


ASSETS = Path(__file__).with_name("prototype_assets")
COMPONENT_KEY = "umbral-prototype"
SYMBOLS = {
    "Overview": '<path d="M3 19l5-9h7l6-6v15z"/>',
    "Documents": '<path d="M3 8h5l2-3h11v14H3zM6 12h11"/>',
    "Classification": '<path d="M7 5h14M3 11h18m-11 6h11"/>',
    "Search": '<circle cx="10" cy="10" r="6"/><path d="m14.5 14.5 6 6"/>',
    "Recommendations": '<path d="M3 6h8l5 6h5M3 18h7l3-4"/>',
    "Assistant": '<path d="M3 5h18v11H10l-5 4v-4H3z"/>',
    "Knowledge Graph": '<path d="m12 3 9 5v9l-9 4-9-4V8zm-9 5 9 4 9-4m-9 4v9"/>',
    "next": '<path d="M4 12h15m-6-6 6 6-6 6"/>',
    "download": '<path d="M12 3v12m-5-5 5 5 5-5M4 20h16"/>',
    "back": '<path d="M20 12H5m6-6-6 6 6 6"/>',
    "menu": '<path d="M3 5h18M3 12h18M3 19h18"/>',
    "brand": '<path class="optical-stroke" d="M5 9h7l4-4h8"/><path d="M3 13h8l4-4h7M1 17h9l4-4h6"/>',
}


def symbol(name):
    return (f'<svg viewBox="0 0 24 24" aria-hidden="true" class="symbol" fill="none" '
            f'stroke="currentColor" stroke-width="1.8" stroke-linejoin="round">{SYMBOLS[name]}</svg>')


def _color_css():
    tokens = json.loads((ASSETS / "tokens.json").read_text(encoding="utf-8"))
    return ":host{" + "".join(f"--{name}:{color};" for name, color in tokens["color"].items()) + "}\n"


def _read(name):
    return (ASSETS / name).read_text(encoding="utf-8")


_COMPONENT = st.components.v2.component(
    "umbral_prototype",
    html='<div id="umbral-root"></div>',
    css=_color_css() + _read("prototype.css") + "\n" + _read("archive.css") + "\n" + _read("classification.css"),
    js=_read("classification.js") + "\n" + _read("archive.js") + "\n" + _read("prototype.js"),
)


def _badge(doc_id):
    return f'<span class="badge">{symbol("brand")}{escape(doc_id)}</span>'


def _route(page, label=None):
    return (f'<button type="button" class="text-action" data-route="{escape(page)}">'
            f'{escape(label or page)}{symbol("next")}</button>')


def _shell(page, has_history):
    links = []
    for name in PAGES:
        active = ' aria-current="page"' if name == page else ""
        note = "<small>Integration pending</small>" if name == "Knowledge Graph" else ""
        links.append(
            f'<button type="button" class="route" data-route="{name}"{active}>'
            f'{symbol(name)}<span>{name}{note}</span></button>'
        )

    clear = ""
    if page == "Assistant":
        disabled = "" if has_history else " disabled"
        clear = ('<footer class="context"><small>Conversation</small>'
                 f'<button type="button" data-confirm{disabled}>Clear conversation</button></footer>')

    rail = (f'<div class="rail-inner"><div class="brand">{symbol("brand")}<strong>UMBRAL</strong></div>'
            '<p class="brand-caption">Knowledge Hub</p>'
            f'<nav aria-label="Main navigation">{"".join(links)}</nav>{clear}</div>')
    return f"""
        <button type="button" class="skip" data-skip>Skip to content</button>
        <aside class="rail">{rail}</aside>
        <header class="mobile-bar">{symbol("brand")}<strong>{page}</strong>
            <button type="button" data-menu aria-haspopup="dialog">{symbol("menu")}Menu</button>
        </header>
        <dialog class="drawer" aria-label="Menu">
            <button type="button" class="drawer-close" data-close-menu>Close</button>{rail}
        </dialog>
        <dialog class="confirm-dialog" aria-labelledby="clear-question">
            <h2 id="clear-question">Clear this conversation?</h2>
            <p>This removes the questions and answers in this session.</p>
            <div class="actions"><button type="button" class="secondary" data-cancel autofocus>Cancel</button>
                <button type="button" class="primary" data-clear>Clear conversation</button></div>
        </dialog>
    """


def _composer(overview=False):
    name = "Overview" if overview else "Assistant"
    placeholder = "Ask about the collection in English…"
    label = "Ask Assistant" if overview else "Send"
    control = (f'<input id="question" name="question" type="text" placeholder="{placeholder}">'
               if overview else
               f'<textarea id="question" name="question" rows="1" placeholder="{placeholder}"></textarea>')
    disabled = "" if overview else " disabled"
    return f"""
        <form class="composer" autocomplete="off" data-composer="{name}">
            <label for="question">Your question</label>
            <div class="composer-row">{control}<button type="submit" class="primary"{disabled}>{label}</button></div>
            <p class="transport-error" id="transport-error" role="alert" hidden>Couldn’t send the question. Try again.</p>
        </form>
    """


def _reader():
    return f"""
        <section class="reader" hidden aria-labelledby="reader-title">
            <div class="reader-body">
                <div class="reader-top">
                    <button type="button" class="text-action reader-back" data-reader-back>{symbol("back")}<span></span></button>
                    <button type="button" class="text-action reader-close" data-reader-back>Close</button>
                    <p class="reader-kicker">Source document</p>
                </div>
                <span class="badge">{symbol("brand")}<span class="reader-id"></span></span>
                <h2 id="reader-title" tabindex="-1"></h2>
                <p class="reader-category"></p><p class="reader-type"></p>
                <p class="reader-original-label" hidden>Original document</p>
                <pre class="reader-original" tabindex="0" aria-label="Original document" hidden></pre>
                <p class="reader-unavailable" hidden>The original document is currently unavailable.</p>
                <section class="reader-preview" hidden><h3>Extracted passage</h3><p></p></section>
                <div class="reader-actions">
                    <button type="button" class="text-action" data-original>Read original{symbol("next")}</button>
                    <a class="text-action" data-download>Download TXT{symbol("next")}</a>
                </div>
                <details class="evidence">
                    <summary>Evidence details</summary>
                    <p class="similarity"></p><p class="sentences"></p>
                    <p>Cosine similarity indicates how closely the document matches the question.</p>
                    <h3>Extracted passage</h3><p class="fragments"></p>
                </details>
            </div>
        </section>
    """


def _overview(documents, feature):
    categories = {}
    for document in documents:
        categories[document.category] = categories.get(document.category, 0) + 1
    category_names = [category_label(category) for category in categories]
    description = ", ".join(category_names[:-1]) + " and " + category_names[-1] if len(category_names) > 1 else "".join(category_names)
    counts = "".join(f'<li>{escape(category_label(category))} · {count} documents</li>'
                     for category, count in categories.items())
    return f"""
        <div class="overview-flow">
            <section class="entry">
                <h1 id="page-title" class="hero-title" tabindex="-1">Ask the <span>collection.</span></h1>
                <p class="entry-description">Find an answer in the team’s documents and follow it back to its source.</p>
                {_composer(overview=True)}
            </section>
            <div class="feature-art">
                {_read("layers.svg")}
                <button type="button" class="feature-toggle" aria-controls="feature-details" aria-expanded="false" data-feature>
                    {_badge(feature['id'])}<span>Featured document</span>
                </button>
            </div>
            <section class="feature">
                <div class="feature-meta">{_badge(feature['id'])}<span>{escape(feature['category'])}</span></div>
                <h2>{escape(feature['title'])}</h2>
                <div id="feature-details" hidden>
                    <p class="feature-category">{escape(feature['category'])}</p>
                    <p class="feature-type">{escape(feature['type'])}<span class="feature-department">
                        · {escape(feature['department'])}</span></p>
                    <div class="actions">
                        <button type="button" class="text-action" id="feature-original" data-feature-original>Read original{symbol("next")}</button>
                        <button type="button" class="text-action" data-hide-feature>Hide details</button>
                        <button type="button" class="text-action" id="feature-in-documents" data-open-in-documents="{escape(feature['id'])}">Open in Documents{symbol("next")}</button>
                    </div>
                </div>
            </section>
            <section class="collection">
                <h2>Inside the collection</h2>
                <p class="count"><strong>{len(documents)} documents</strong><span>/</span>{len(categories)} categories</p>
                <p>{escape(description.capitalize())}.</p>
                <details class="category-counts"><summary>Documents by category</summary><ul>{counts}</ul></details>
                <div class="actions">{_route("Documents", "Browse documents")}{_route("Recommendations")}</div>
            </section>
        </div>
        {_reader()}
    """


def _assistant(history):
    if not history:
        suggestions = "".join(
            f'<button type="button" class="suggestion" data-suggest="{index}">{escape(question)}{symbol("next")}</button>'
            for index, question in enumerate(EXAMPLE_QUESTIONS)
        )
        conversation = f"""
            <p class="assistant-mark">{symbol("brand")}Assistant</p>
            <h1 id="page-title" class="hero-title" tabindex="-1">What would you <span>like to find?</span></h1>
            <p class="welcome-description">Ask in English about the collection. Each question is answered
                independently using passages from the original documents.</p>
            <section class="suggestions"><h2>Try a question</h2><div>{suggestions}</div></section>
        """
    else:
        turns = [_turn(index, user, answer) for index, (user, answer) in
                 enumerate(zip(history[::2], history[1::2]))]
        index_controls = ""
        if len(turns) > 1:
            questions = "".join(
                f'<li><button type="button" class="text-action" data-turn-link="{index}">{escape(user["content"])}</button></li>'
                for index, user in enumerate(history[::2])
            )
            index_controls = ('<div class="history-tools"><details class="previous"><summary>Previous questions</summary>'
                              f'<ol>{questions}</ol></details><button type="button" class="text-action" data-latest>Latest answer</button></div>')
        conversation = (f'<div class="conversation-heading"><h1 id="page-title" tabindex="-1">{symbol("brand")}Assistant</h1>'
                        f'{index_controls}</div><div class="turns" tabindex="0" aria-label="Conversation">'
                        f'{"".join(turns)}</div>')
    return f"""
        <div class="assistant-workspace {'has-turns' if history else 'welcome'}">
            <div class="assistant-main">{conversation}{_composer()}</div>
            {_reader()}
        </div>
    """


def _turn(index, user, turn):
    question = escape(user["content"])
    response = turn.get("response")
    if turn["status"] == "error":
        answer = (f'<div class="notice error" role="alert" id="turn-error-{index}">Couldn’t retrieve an answer. '
                  f'<button type="button" class="text-action" data-retry="{index}">Retry</button></div>')
    elif response is None:
        answer = '<p role="status" class="notice processing">Finding passages…</p>'
    elif not response.answered:
        answer = (f'<div class="notice abstention"><p>{escape(response.answer)}</p>'
                  '<button type="button" class="text-action" data-rephrase>Rephrase your question</button></div>')
    else:
        references = "".join(
            f'<button type="button" class="source-trigger text-action" id="source-{index}-{escape(source.document_id)}"'
            f' data-source="{escape(source.document_id)}" data-source-turn="{index}">'
            f'{_badge(source.document_id)}<span>View source</span>{symbol("next")}</button>'
            for source in response.sources
        )
        passages = []
        for section in response.answer.split("\n\n"):
            attribution, separator, body = section.partition("\n")
            passages.append(f'<p class="attribution">{escape(attribution)}</p><p>{escape(body)}</p>' if separator
                            else f'<p>{escape(section)}</p>')
        answer = (f'<div class="passages">{"".join(passages)}</div>'
                  f'<div class="source-controls">{references}</div>')
    return (f'<article class="turn" data-turn="{index}"><span class="role">You</span>'
            f'<h2 id="turn-{index}" tabindex="-1">{question}</h2>'
            f'<span class="role assistant-role">{symbol("brand")}Assistant</span>{answer}</article>')


def _assistant_sources(documents, history):
    evidence = {}
    available_ids = set()
    for index, turn in enumerate(history[1::2]):
        response = turn.get("response")
        if response is None:
            continue
        for source in response.sources:
            fragments = [fragment.text for fragment in response.fragments if fragment.document_id == source.document_id]
            evidence[f"{index}-{source.document_id}"] = {
                "id": source.document_id, "title": source.title, "category": category_label(source.category),
                "similarity": f"{source.similarity:.6f}", "fragments": fragments,
            }
            available_ids.add(source.document_id)
    return {doc.doc_id: document_payload(doc) for doc in documents if doc.doc_id in available_ids}, evidence


def render_prototype(retrieval, chatbot):
    state = st.session_state
    state.setdefault("navigation", "Overview")
    state.setdefault(REVISION_KEY, uuid4().hex)
    state.setdefault(HISTORY_KEY, [])

    def on_action():
        action = state[COMPONENT_KEY].action
        if handle_classification_action(state, action):
            return
        if not handle_library_action(state, action, retrieval.documents):
            remember_library_query(state, action, retrieval.documents)
            handle_action(state, action, chatbot)

    page = state["navigation"]
    history = state[HISTORY_KEY]
    evidence = {}
    documents = {}
    archive = None
    classification = None
    if page == "Overview":
        feature = next(doc for doc in retrieval.documents if doc.doc_id == "UW04")
        documents[feature.doc_id] = document_payload(feature)
        content = _overview(retrieval.documents, documents[feature.doc_id])
    elif page == "Assistant":
        documents, evidence = _assistant_sources(retrieval.documents, history)
        content = _assistant(history)
    elif page == "Documents":
        content, archive = render_archive(state, retrieval.documents, _badge, symbol)
    elif page == "Classification":
        content, classification = render_classification(state)
    else:
        content = ""
    crumb = f'<p class="crumb">Knowledge Hub <span>/</span> <strong>{page}</strong></p>'
    markup = (f'{_shell(page, bool(history))}<div class="page page-{page.lower().replace(" ", "-")}"'
              f' id="page-content"><div class="page-inner">{crumb}{content}</div></div><div class="announcements" role="status"></div>')
    st.html(ASSETS / "host.css")
    with st.container(key="umbral-frame"):
        _COMPONENT(
            key=COMPONENT_KEY, on_action_change=on_action,
            data={"page": page, "markup": markup, "revision": state[REVISION_KEY], "documents": documents,
                  "evidence": evidence, "archive": archive, "classification": classification, "suggestions": EXAMPLE_QUESTIONS, "turns": len(history) // 2},
        )
    return page
