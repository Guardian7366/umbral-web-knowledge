"""Shared document presentation and native search view."""

from __future__ import annotations

import streamlit as st

CATEGORY_LABELS = {
    "design_references": "Design references",
    "creative_methods": "Creative methods",
    "project_lessons": "Project lessons",
}


def category_label(category: str) -> str:
    """Return a readable category name."""

    return CATEGORY_LABELS.get(
        category,
        category.replace("_", " ").title(),
    )


def render_document_content(document) -> None:
    """Display the original document and its metadata."""

    st.caption(
        f"{document.doc_id} | "
        f"{category_label(document.category)}"
    )

    original_text = document.path.read_text(
        encoding="utf-8-sig"
    )

    st.text(original_text)

    st.download_button(
        label="Download original document",
        data=document.path.read_bytes(),
        file_name=document.path.name,
        mime="text/plain",
        key=f"download_{document.doc_id}",
    )


def render_search(retrieval) -> None:
    """Display document retrieval results."""

    st.title("Knowledge search")

    st.write(
        "Find relevant documents using the "
        "internal knowledge collection."
    )

    with st.form("search_form"):

        query = st.text_input(
            "Search query",
            placeholder=(
                "How can we organize a design session?"
            ),
        )

        top_k = st.slider(
            "Maximum results",
            min_value=1,
            max_value=len(retrieval.documents),
            value=3,
        )

        submitted = st.form_submit_button(
            "Search documents",
            type="primary",
        )

    if submitted:

        st.session_state.pop(
            "document_search_result",
            None,
        )

        if not query.strip():

            st.warning(
                "Please enter a search query."
            )

            return

        results = retrieval.search(
            query.strip(),
            top_k=top_k,
        )

        st.session_state["document_search_result"] = {
            "query": query.strip(),
            "results": results,
        }

    search_result = st.session_state.get(
        "document_search_result"
    )

    if search_result is None:
        return

    results = search_result["results"]

    st.divider()

    st.subheader("Search results")

    st.caption(
        f"Query: {search_result['query']}"
    )

    st.caption(
        f"{len(results)} relevant documents found"
    )

    if not results:

        st.info(
            "No relevant documents were found "
            "for this query."
        )

        return

    for position, result in enumerate(
        results,
        start=1,
    ):

        document = result.document

        with st.container(border=True):

            st.caption(
                f"Result {position} | "
                f"{document.doc_id}"
            )

            st.markdown(
                f"**{document.title}**"
            )

            st.write(
                category_label(document.category)
            )

            st.caption(
                f"Cosine similarity: "
                f"{result.similarity:.6f}"
            )

            with st.expander("View original document"):

                render_document_content(document)

    st.caption(
        "Cosine similarity measures lexical "
        "relatedness. It is not a confidence "
        "probability or an accuracy percentage."
    )