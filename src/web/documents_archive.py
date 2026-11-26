"""Catalog-backed index and single original reader for Documents."""

import base64
from html import escape
from uuid import uuid4

from src.web.chatbot_view import REVISION_KEY
from src.web.document_views import CATEGORY_LABELS, category_label


LIBRARY_ACTIONS = {
    "open_document", "library_open", "library_query", "library_category",
    "library_group", "library_reset", "library_clear", "library_restore",
    "library_back", "library_origin", "library_retry",
}


def document_payload(document):
    """Decode the original for reading and keep its bytes for download."""
    try:
        raw = document.path.read_bytes()
        original = raw.decode("utf-8-sig", errors="replace")
        available = True
    except OSError:
        raw, original, available = b"", "", False

    metadata = {}
    for line in original.splitlines()[:5]:
        name, _, value = line.partition(":")
        metadata[name] = value.strip()
    return {
        "id": document.doc_id, "title": document.title, "category": category_label(document.category),
        "type": metadata.get("Type", ""), "department": metadata.get("Responsible department", ""),
        "original": original, "bytes": base64.b64encode(raw).decode("ascii"), "file": document.path.name,
        "available": available,
    }


def _library(state):
    state.setdefault("library_category", "all")
    state.setdefault("library_query", "")
    return state.setdefault("document_library", {})


def _matches(documents, category, query):
    query = query.strip().lower()
    return [
        doc for doc in documents if (category == "all" or doc.category == category)
        and query in f"{doc.doc_id} {doc.title} {doc.text}".lower()
    ]


def _visible(documents, state):
    return _matches(documents, state["library_category"], state["library_query"])


def _reconcile(library, matches):
    categories = {doc.category for doc in matches}
    if library.get("group") not in categories:
        library["group"] = matches[0].category if matches else None
    if library.get("selected") not in {doc.doc_id for doc in matches}:
        if library.get("reading"):
            library["notice"] = "The selected document is outside these filters."
        library["reading"] = False
        library["selected"] = None


def remember_library_query(state, action, documents):
    """Keep the last typed value if navigation precedes its search request."""
    if state.get("navigation") != "Documents" or not isinstance(action, dict):
        return
    if action.get("kind") == "navigate" and action.get("revision") == state[REVISION_KEY]:
        query = action.get("query")
        if isinstance(query, str) and query != state["library_query"]:
            library = _library(state)
            state["library_query"] = query
            _reconcile(library, _visible(documents, state))


def handle_library_action(state, action, documents):
    """Accept one revision-bound intention using catalog IDs only."""
    if not isinstance(action, dict) or not isinstance(action.get("kind"), str) or action["kind"] not in LIBRARY_ACTIONS:
        return False
    kind = action["kind"]
    if action.get("revision") != state[REVISION_KEY]:
        return True
    page = state["navigation"]
    if kind != "open_document" and page != "Documents":
        return True

    library = _library(state)
    library["notice"] = ""
    state[REVISION_KEY] = uuid4().hex

    if kind in ("open_document", "library_open"):
        if kind == "library_open" and isinstance(action.get("query"), str):
            state["library_query"] = action["query"]
        matches = _visible(documents, state)
        candidates = documents if kind == "open_document" else matches
        doc = next((item for item in candidates if item.doc_id == action.get("id")), None)
        if kind == "open_document":
            state["navigation"] = "Documents"
            if page == "Overview":
                library["origin"] = page
        if doc is None:
            library["notice"] = "Document not found."
            _reconcile(library, matches)
            return True
        if kind == "open_document" and doc not in matches:
            library.setdefault("suspended", (state["library_category"], state["library_query"], library.get("group")))
            state["library_category"], state["library_query"] = "all", ""
        library.update(group=doc.category, selected=doc.doc_id, reading=True)
        return True

    if kind == "library_origin" and library.get("origin") == "Overview":
        library.update(origin=None, reading=False)
        state["navigation"] = "Overview"
        return True
    if kind == "library_back":
        library["reading"] = False
        if isinstance(action.get("id"), str) and action["id"] == library.get("selected"):
            doc = next((item for item in documents if item.doc_id == action["id"]), None)
            if doc is not None:
                library["group"] = doc.category
        return True
    if kind == "library_retry":
        return True

    if kind == "library_reset":
        state["library_category"], state["library_query"] = "all", ""
        library["group"] = None
    elif kind == "library_clear":
        state["library_query"] = ""
    elif kind == "library_restore" and library.get("suspended"):
        state["library_category"], state["library_query"], library["group"] = library.pop("suspended")
        library["reading"] = False
    else:
        if isinstance(action.get("query"), str):
            state["library_query"] = action["query"]
        if kind == "library_category" and action.get("category") in ("all", *CATEGORY_LABELS):
            state["library_category"] = action["category"]
            library["group"] = None
        if kind == "library_group" and isinstance(action.get("category"), str) and action["category"] in CATEGORY_LABELS:
            if library.get("group") != action["category"]:
                library.update(group=action["category"], reading=False)

    _reconcile(library, _visible(documents, state))
    return True


def _divider(category, group, records, selected, symbol):
    label = escape(category_label(category))
    expanded = category == group
    first, last = records[0].doc_id, records[-1].doc_id
    document_range = escape(first if first == last else f"{first} – {last}")
    heading = (
        f'<button class="archive-divider" type="button" id="archive-group-{category}"'
        f' data-archive-group="{category}" aria-expanded="{str(expanded).lower()}" aria-controls="archive-list-{category}">'
        '<span class="archive-divider-face" aria-hidden="true" data-opening-divider></span>'
        f'<span class="archive-divider-text"><strong>{label}</strong>'
        f'<span class="archive-range">{"Open · " if expanded else ""}{document_range}</span></span>'
        f'<span class="archive-group-count" aria-label="{len(records)} documents">{len(records)}</span>'
        '<span class="archive-chevron" aria-hidden="true"></span></button>'
    )
    sheets = []
    if expanded:
        for index, doc in enumerate(records):
            doc_id = escape(doc.doc_id)
            chosen = doc.doc_id == selected
            marker = '<span class="archive-selected">Selected</span>' if chosen else ""
            sheets.append(
                f'<li style="--sheet-order:{index}"><button type="button" class="archive-sheet"'
                f' id="archive-sheet-{doc_id}" data-archive-open="{doc_id}" aria-pressed="{str(chosen).lower()}">'
                '<span class="archive-paper" aria-hidden="true" data-opening-sheet></span>'
                f'<span class="archive-sheet-id">{doc_id}</span>'
                f'{marker}'
                f'<strong>{escape(doc.title)}</strong>{symbol("next")}</button></li>'
            )
    hidden = "" if expanded else " hidden"
    return (f'<div class="archive-group">{heading}<ul id="archive-list-{category}" class="archive-sheets"'
            f' aria-labelledby="archive-group-{category}"{hidden}>{"".join(sheets)}</ul></div>')


def _reader(doc, badge, symbol):
    available = doc["available"]
    content = (
        f'<pre class="archive-original" tabindex="0" aria-label="Original document">{escape(doc["original"])}</pre>'
        if available else
        '<div role="alert" class="archive-error"><p>The original document is currently unavailable.</p>'
        '<button type="button" class="text-action" data-archive-action="library_retry">Retry</button></div>'
    )
    download = (
        f'<a class="secondary archive-download" href="data:text/plain;base64,{doc["bytes"]}"'
        f' download="{escape(doc["file"])}">{symbol("download")}Download TXT</a>'
        if available else '<button type="button" class="secondary" disabled title="Original unavailable">Download TXT</button>'
    )
    return f"""
        <article class="archive-reader" aria-labelledby="archive-reader-title" data-document-id="{escape(doc['id'])}">
            <div class="archive-reader-top">
                <div class="archive-reader-badge">{badge(doc['id'])}<span>{escape(doc['category'])}</span></div>
                <button type="button" class="text-action archive-back" data-archive-action="library_back">
                    {symbol('back')}Back to index
                </button>
            </div>
            <h2 id="archive-reader-title" tabindex="-1">{escape(doc['title'])}</h2>
            <div class="archive-reader-actions"><strong>Original document</strong>{download}</div>
            {content}
        </article>
    """


def render_archive(state, documents, badge, symbol):
    library = _library(state)
    matches = _visible(documents, state)
    _reconcile(library, matches)
    grouped = {category: [doc for doc in matches if doc.category == category] for category in CATEGORY_LABELS}
    grouped = {category: records for category, records in grouped.items() if records}
    group = library.get("group")
    selected = library.get("selected")
    original = next((doc for doc in matches if doc.doc_id == selected), None) if library.get("reading") else None
    opening = bool(matches and not original and not library.get("opening_seen"))
    if matches:
        library["opening_seen"] = True
    query = state["library_query"]
    filtered = bool(query.strip() or state["library_category"] != "all")
    options = "".join(f'<option value="{value}"{" selected" if state["library_category"] == value else ""}>{label}</option>'
                      for value, label in {"all": "All categories", **CATEGORY_LABELS}.items())
    count = f"Showing {len(matches)} of {len(documents)} documents"
    dividers = "".join(_divider(category, group, records, selected, symbol) for category, records in grouped.items())
    open_label = escape(category_label(group)) if group else ""
    tray = (f'<div class="archive-tray" style="--group-count:{len(grouped)}">{dividers}'
            '<div class="archive-lip" aria-hidden="true"></div>'
            f'<div class="archive-tray-front"><strong>{open_label}</strong><span>{len(grouped[group])} documents</span>'
            f'<span>Collection / {len(documents)} documents</span></div></div>') if grouped else (
                '<p class="archive-empty" role="status">No documents match the selected filters.</p>'
            )
    extra = []
    if query:
        extra.append(("library_clear", "Clear search"))
    if query or state["library_category"] != "all":
        extra.append(("library_reset", "Reset filters"))
    if library.get("suspended"):
        extra.append(("library_restore", "Restore previous filters"))
    if library.get("origin"):
        extra.append(("library_origin", "Back to Overview"))
    actions = "".join(f'<button type="button" class="text-action" data-archive-action="{action}">'
                      f'{symbol("back") if action == "library_origin" else ""}{label}</button>' for action, label in extra)
    notice = f'<p class="archive-notice" role="status">{escape(library["notice"])}</p>' if library.get("notice") else ""
    if not documents:
        notice = ('<div role="alert" class="archive-error">Couldn’t load the collection. '
                  '<button type="button" class="text-action" data-archive-action="library_retry">Retry</button></div>')

    html = f"""
        <div class="archive {'archive-reading' if original else ''}"{' data-filtered' if filtered else ''}>
            <header class="archive-heading">
                <h1 id="page-title" tabindex="-1">Documents</h1>
                <p>Open a category divider, then select a document to read its original text.</p>
            </header>
            <div class="archive-controls">
                <label for="archive-query">Search library
                    <span class="archive-input">{symbol('Search')}
                        <input id="archive-query" type="search" value="{escape(query)}" placeholder="Document ID, title, or content">
                    </span>
                </label>
                <label for="archive-category">Filter by category
                    <select id="archive-category">{options}</select>
                </label>
            </div>
            <div class="archive-actions">{actions}</div>
            {notice}
            <div class="archive-layout">
                <section class="archive-index" aria-labelledby="archive-index-title">
                    <div class="archive-index-heading">
                        <h2 id="archive-index-title">Document index</h2>
                        <span role="status">{count if query or state["library_category"] != "all" else f"{len(documents)} documents"}</span>
                    </div>
                    {tray}
                    <p class="archive-match-count" role="status">{count}</p>
                </section>
                {_reader(document_payload(original), badge, symbol) if original else ""}
            </div>
        </div>
    """
    return html, {
        "opening": opening, "matchingIds": [doc.doc_id for doc in matches],
        "selected": selected, "group": group, "reading": original is not None,
        "query": query, "collectionSize": len(documents),
    }
