"""Lexical search and shared ranking/reader presentation."""

from html import escape
import logging
from uuid import uuid4

from src.web.chatbot_view import REVISION_KEY
from src.web.document_views import category_label
from src.web.documents_archive import document_payload, render_original_reader

LOGGER = logging.getLogger(__name__)


def limit_control(limit, maximum):
    options = "".join(
        f'<option value="{number}"{" selected" if number == limit else ""}>{number}</option>'
        for number in range(1, maximum + 1)
    )
    return f'<label class="tool-limit">Maximum results<select name="limit">{options}</select></label>'


def heading(title, mobile_title, description):
    return f"""
        <header class="tool-heading">
            <h1 id="page-title" tabindex="-1"><span>{title}</span><span>{mobile_title}</span></h1>
            <p>{description}</p>
        </header>
    """


def feedback(state, submit_label, waiting):
    notice = state.get("notice")
    message = f'<p>{escape(notice[1])}</p>' if notice else ""
    if notice and notice[0] == "error":
        message += '<button class="text-action" type="submit" name="retry">Retry</button>'
    return f"""
        <button class="primary tool-submit" type="submit">{submit_label}</button>
        <p role="status" class="tool-wait" hidden>{waiting}</p>
        <div role="status" id="tool-notice" data-status="{notice[0] if notice else ''}"
             {'' if notice else 'hidden'}>{message}</div>
    """


def index_heading(count, noun, description=""):
    subtitle = f'<p>{description}</p>' if description else ""
    return (f'<h2 class="tool-count" id="tool-index-title" tabindex="-1">'
            f'{count} {noun}{"s" if count != 1 else ""}</h2>{subtitle}')


def rank_item(position, document, symbol, active, expanded=None, panel=""):
    identifier = escape(document.doc_id)
    name = escape(document.title)
    category = escape(category_label(document.category))
    search = expanded is None
    command = "tool_open" if search else "tool_inspect"
    state = (' aria-current="true"' if active else "") if search else f' aria-expanded="{str(expanded).lower()}"'
    if not search and expanded:
        state += f' aria-controls="tool-explanation-{identifier}"'
    description = f'<span class="tool-why">Why this document?</span>' if not search and expanded else ""
    return f"""
        <li class="tool-row{' is-active' if active else ''}" data-id="{identifier}">
            <button type="button" class="tool-record" data-tool-action="{command}" data-id="{identifier}"{state}>
                <span class="tool-order" aria-label="Rank {position}">{position:02}</span>
                <span class="tool-record-body">
                    <span class="tool-meta"><strong>{identifier}</strong><span>{category}</span></span>
                    <strong class="tool-result-title">{name}</strong>{description}
                </span>
                {symbol('next') if search else '<span class="tool-chevron" aria-hidden="true"></span>'}
            </button>
            {panel}
        </li>
    """


def match_details(label, result, markup):
    return f"""
        <details class="tool-match" id="match-{escape(result.document.doc_id)}">
            <summary>Match details <small>{label} · Cosine similarity {result.similarity:.6f}</small></summary>
            {markup}
        </details>
    """


def original_reader(result, badge, symbol, details="", back_label="Back to results"):
    return render_original_reader(
        document_payload(result.document), badge, symbol,
        actions='data-tool-action', back="tool_back", retry="tool_retry_file",
        back_label=back_label, trailing=details,
    )


def get_tool_state(state, key, initial):
    return state.setdefault(key, initial)


def handle_ranking_action(tool, action, batch):
    identifier = action.get("documentId")
    kind = action.get("kind")
    if kind in ("tool_open", "tool_inspect"):
        if isinstance(identifier, str) and any(item.document.doc_id == identifier for item in batch["results"]):
            tool["selected"] = identifier
            if kind == "tool_inspect":
                tool["expanded"] = None if tool.get("expanded") == identifier else identifier
            else:
                tool["reading"] = True
    elif kind == "tool_back":
        tool["reading"] = False
    # tool_retry_file rerenders the reader and reopens its original bytes.


def handle_search_action(state, action, retrieval):
    kind = action.get("kind")
    tool = get_tool_state(state, "search_view", {"draft": {"query": "", "limit": 3}})
    if kind in ("navigate", "tool_submit"):
        draft = action.get("toolDraft")
        if isinstance(draft, dict):
            query, limit = draft.get("query"), draft.get("limit")
            if isinstance(query, str) and type(limit) is int and 1 <= limit <= len(retrieval.documents):
                tool["draft"] = {"query": query, "limit": limit}
    if kind == "navigate":
        tool["reading"] = False
        return
    state[REVISION_KEY] = uuid4().hex
    if kind != "tool_submit":
        batch = state.get("document_search_result")
        if batch:
            handle_ranking_action(tool, action, batch)
        return

    query = tool["draft"]["query"].strip()
    top_k = tool["draft"]["limit"]
    state.pop("document_search_result", None)
    tool.update(notice=None, reading=False, selected=None)
    if not query:
        tool["notice"] = ("empty", "Enter a search query.")
        return
    try:
        results = retrieval.search(query, top_k=top_k)
    except Exception:
        LOGGER.exception("Search failed")
        tool["notice"] = ("error", "Couldn’t search the collection.")
        return
    state["document_search_result"] = {"query": query, "top_k": top_k, "results": results}


def render_search(state, retrieval, badge, symbol):
    tool = get_tool_state(state, "search_view", {"draft": {"query": "", "limit": 3}})
    draft = tool["draft"]
    batch = state.get("document_search_result")
    index, reader = "", ""
    if batch:
        results = batch["results"]
        rows = "".join(rank_item(i, result.document, symbol, result.document.doc_id == tool.get("selected"))
                       for i, result in enumerate(results, 1))
        matches = (f'<ol class="tool-ranking" aria-labelledby="tool-index-title">{rows}</ol>' if rows else
                   '<p class="tool-empty">No matching documents. Try different words.</p>')
        index = f"""
            <section class="tool-index" aria-labelledby="tool-index-title">
                {index_heading(len(results), 'result', 'Ordered by word match' if rows else '')}
                {matches}
            </section>
        """
        if tool.get("reading"):
            selected = next((result for result in results if result.document.doc_id == tool.get("selected")), None)
            if selected:
                details = match_details("TF-IDF", selected, f"""
                    <p>Query: {escape(batch['query'])}</p><p>Maximum results: {batch['top_k']}</p>
                    <p>Cosine similarity measures overlap in weighted words and phrases.</p>
                """)
                reader = original_reader(selected, badge, symbol, details)
    markup = f"""
        <div class="tool-workspace tool-search{' is-reading' if reader else ''}">
            {heading('Search', 'Find documents', 'Find documents that share words with your question.')}
            <form class="tool-form" autocomplete="off">
                <label class="tool-query">Your question or keywords
                    <span>{symbol('Search')}<textarea rows="1" name="query" aria-describedby="tool-notice"
                        placeholder="How can we organize a design session?">{escape(draft['query'])}</textarea></span>
                </label>
                {limit_control(draft['limit'], len(retrieval.documents))}
                {feedback(tool, 'Find documents', 'Finding documents…')}
            </form>
            <p class="tool-dirty" hidden>Search again to use the edited criteria.</p>
            <div class="tool-layout">{index}{reader}</div>
        </div>
    """
    confirmed = {"query": batch["query"], "limit": batch["top_k"]} if batch else None
    return markup, {"confirmed": confirmed, "selected": tool.get("selected"), "count": len(batch["results"]) if batch else 0}
