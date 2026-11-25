"""Web interface for the document recommendation system."""

from __future__ import annotations

import streamlit as st

from src.web.document_views import (
    category_label,
    render_document_content,
)


def render_recommendations(recommender) -> None:
    """Display recommendations based on documents or search queries."""

    st.title("Knowledge recommendations")

    st.write(
        "Discover related knowledge based on a selected "
        "document or your current search context."
    )

    documents = recommender.retrieval.documents

    document_by_id = {
        document.doc_id: document
        for document in documents
    }

    mode = st.radio(
        "Recommendation mode",
        options=[
            "By document",
            "By search query",
        ],
        horizontal=True,
        key="recommendation_mode",
    )

    with st.form("recommendation_form"):

        if mode == "By document":

            selected_document = st.selectbox(
                "Select a source document",
                options=list(document_by_id),
                format_func=lambda document_id: (
                    f"{document_id} - "
                    f"{document_by_id[document_id].title}"
                ),
            )

            query = ""

        else:

            selected_document = None

            query = st.text_input(
                "Search context",
                placeholder=(
                    "How can we organize "
                    "a design session?"
                ),
            )

        top_k = st.slider(
            "Maximum recommendations",
            min_value=1,
            max_value=8 if mode == "By document" else 9,
            value=3,
        )

        with st.expander("Advanced settings"):

            min_similarity = st.slider(
                "Minimum cosine similarity",
                min_value=0.0,
                max_value=1.0,
                value=0.0,
                step=0.01,
            )

            st.caption(
                "Increase this threshold to exclude "
                "documents with weaker lexical similarity."
            )

        submitted = st.form_submit_button(
            "Get recommendations",
            type="primary",
        )

    if submitted:

        st.session_state.pop(
            "recommendation_result",
            None,
        )

        if mode == "By document":

            results = recommender.recommend_by_document(
                selected_document,
                top_k=top_k,
                min_similarity=min_similarity,
            )

            context = (
                f"{selected_document} - "
                f"{document_by_id[selected_document].title}"
            )

        else:

            if not query.strip():

                st.warning(
                    "Please enter a search query."
                )

                return

            results = recommender.recommend_by_query(
                query.strip(),
                top_k=top_k,
                min_similarity=min_similarity,
            )

            context = query.strip()

        st.session_state["recommendation_result"] = {
            "mode": mode,
            "context": context,
            "results": results,
            "top_k": top_k,
            "min_similarity": min_similarity,
        }

    saved_result = st.session_state.get(
        "recommendation_result"
    )

    if saved_result is None:
        return

    if saved_result["mode"] != mode:
        return

    results = saved_result["results"]

    st.divider()

    st.subheader("Recommended documents")

    st.caption(
        f"Mode: {saved_result['mode']}"
    )

    st.caption(
        f"Context: {saved_result['context']}"
    )

    st.caption(
        f"{len(results)} recommendations found"
    )

    if not results:

        st.info(
            "No relevant recommendations were found "
            "for the selected context and settings."
        )

        return

    for position, result in enumerate(
        results,
        start=1,
    ):

        document = result.document

        with st.container(border=True):

            st.caption(
                f"Recommendation {position} | "
                f"{document.doc_id}"
            )

            st.subheader(document.title)

            first, second = st.columns(2)

            with first:

                st.write(
                    category_label(
                        document.category
                    )
                )

            with second:

                st.metric(
                    "Cosine similarity",
                    f"{result.similarity:.6f}",
                )

            st.markdown("**Why this document?**")

            st.write(result.explanation)

            st.markdown("**Shared relevant terms**")

            if result.shared_terms:

                st.write(
                    " | ".join(
                        result.shared_terms
                    )
                )

            else:

                st.caption(
                    "No shared terms available."
                )

            with st.expander(
                "View original document"
            ):

                render_document_content(document)

    st.caption(
        "Recommendations use TF-IDF and cosine "
        "similarity. Scores represent lexical "
        "relatedness, not confidence probabilities."
    )

    with st.expander(
        "About the recommendation system"
    ):

        st.write(
            "The system compares weighted text "
            "representations from the internal "
            "document collection."
        )

        st.write(
            "Document-based recommendations exclude "
            "the selected source document."
        )

        st.write(
            "Search-context recommendations use "
            "the current query without storing "
            "persistent user histories."
        )