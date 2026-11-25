"""Web interface for lexical and semantic recommendations."""

from __future__ import annotations

import logging

import streamlit as st

from src.web.document_views import (
    category_label,
    render_document_content,
)


LOGGER = logging.getLogger(__name__)

LEXICAL_METHOD = "Lexical (TF-IDF)"
SEMANTIC_METHOD = "Semantic (BGE)"

METHOD_DESCRIPTIONS = {
    LEXICAL_METHOD: (
        "Find related documents using weighted vocabulary "
        "and lexical similarity."
    ),
    SEMANTIC_METHOD: (
        "Find conceptually related documents using "
        "contextual text embeddings."
    ),
}

DEFAULT_THRESHOLDS = {
    LEXICAL_METHOD: 0.0,
    SEMANTIC_METHOD: 0.55,
}


@st.cache_resource
def initialize_semantic_engine(_retrieval):
    """Initialize the semantic engine only when requested.

    The retrieval argument is excluded from Streamlit hashing.
    This application uses a single fixed document collection.
    """

    from src.semantic_recommender import (
        SemanticRecommendationEngine,
    )

    return SemanticRecommendationEngine(_retrieval)


def render_recommendations(recommender) -> None:
    """Display lexical or semantic recommendations."""

    st.title("Knowledge recommendations")

    st.write(
        "Discover related knowledge based on a selected "
        "document or your current search context."
    )

    method = st.radio(
        "Recommendation method",
        options=[
            LEXICAL_METHOD,
            SEMANTIC_METHOD,
        ],
        horizontal=True,
        key="recommendation_method",
    )

    st.caption(
        METHOD_DESCRIPTIONS[method]
    )

    is_semantic = method == SEMANTIC_METHOD

    if is_semantic:

        st.info(
            "Semantic recommendations use the "
            "BAAI/bge-small-en-v1.5 embedding model. "
            "The first request may require a model "
            "download and initialization."
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

    method_key = (
        "semantic"
        if is_semantic
        else "lexical"
    )

    mode_key = (
        "document"
        if mode == "By document"
        else "query"
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
                    "How can we brainstorm "
                    "new concepts as a team?"
                ),
            )

        maximum_results = (
            len(documents) - 1
            if mode == "By document"
            else len(documents)
        )

        top_k = st.slider(
            "Maximum recommendations",
            min_value=1,
            max_value=maximum_results,
            value=min(3, maximum_results),
            key=f"recommendation_limit_{mode_key}",
        )

        with st.expander("Advanced settings"):

            min_similarity = st.slider(
                "Minimum cosine similarity",
                min_value=0.0,
                max_value=1.0,
                value=DEFAULT_THRESHOLDS[method],
                step=0.01,
                key=f"recommendation_threshold_{method_key}",
            )

            if is_semantic:

                st.caption(
                    "The initial semantic threshold of "
                    "0.55 is based on preliminary "
                    "functional validation."
                )

            else:

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

        if (
            mode == "By search query"
            and not query.strip()
        ):

            st.warning(
                "Please enter a search query."
            )

            return

        try:

            with st.spinner(
                "Retrieving related knowledge..."
            ):

                if is_semantic:

                    engine = initialize_semantic_engine(
                        recommender.retrieval
                    )

                else:

                    engine = recommender

                if mode == "By document":

                    results = engine.recommend_by_document(
                        selected_document,
                        top_k=top_k,
                        min_similarity=min_similarity,
                    )

                    context = (
                        f"{selected_document} - "
                        f"{document_by_id[selected_document].title}"
                    )

                else:

                    results = engine.recommend_by_query(
                        query.strip(),
                        top_k=top_k,
                        min_similarity=min_similarity,
                    )

                    context = query.strip()

        except Exception:

            LOGGER.exception(
                "Recommendation processing failed."
            )

            if is_semantic:

                st.error(
                    "Semantic recommendations could not "
                    "be generated. Please retry or select "
                    "the lexical recommendation method."
                )

            else:

                st.error(
                    "Recommendations could not be "
                    "generated. Please try again."
                )

            return

        st.session_state["recommendation_result"] = {
            "method": method,
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

    if saved_result["method"] != method:
        return

    results = saved_result["results"]

    st.divider()

    st.subheader("Recommended documents")

    st.caption(
        f"Method: {saved_result['method']}"
    )

    st.caption(
        f"Mode: {saved_result['mode']}"
    )

    st.caption(
        f"Context: {saved_result['context']}"
    )

    st.caption(
        f"Minimum similarity: "
        f"{saved_result['min_similarity']:.2f}"
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

            first, second = st.columns([2, 1])

            with first:

                st.write(
                    category_label(
                        document.category
                    )
                )

                st.caption(
                    "Semantic embedding similarity"
                    if is_semantic
                    else "Lexical TF-IDF similarity"
                )

            with second:

                st.metric(
                    "Cosine similarity",
                    f"{result.similarity:.6f}",
                )

            st.markdown("**Why this document?**")

            st.write(result.explanation)

            terms_heading = (
                "Supplementary shared lexical terms"
                if is_semantic
                else "Shared relevant terms"
            )

            st.markdown(
                f"**{terms_heading}**"
            )

            if result.shared_terms:

                st.write(
                    " | ".join(
                        result.shared_terms
                    )
                )

            else:

                st.caption(
                    "No shared terms were found "
                    "in the TF-IDF vocabulary."
                )

            if is_semantic:

                st.caption(
                    "Shared lexical terms are supplementary "
                    "evidence and do not determine the "
                    "semantic ranking."
                )

            with st.expander(
                "View original document"
            ):

                render_document_content(document)

    if is_semantic:

        st.caption(
            "Semantic scores measure cosine similarity "
            "between contextual embeddings. They are "
            "not confidence probabilities."
        )

    else:

        st.caption(
            "Lexical scores measure cosine similarity "
            "between TF-IDF vectors. They are "
            "not confidence probabilities."
        )

    with st.expander(
        "About the recommendation system"
    ):

        st.markdown("**Lexical recommendations**")

        st.write(
            "TF-IDF represents documents using weighted "
            "terms and compares their lexical similarity."
        )

        st.markdown("**Semantic recommendations**")

        st.write(
            "BAAI/bge-small-en-v1.5 represents document "
            "titles and content using 384-dimensional "
            "contextual embeddings."
        )

        st.write(
            "The semantic model runs locally on CPU "
            "through FastEmbed and ONNX Runtime."
        )

        st.markdown("**Shared behavior**")

        st.write(
            "Both methods exclude the selected source "
            "document in document-based recommendations."
        )

        st.write(
            "Search-context recommendations use the "
            "current query without storing persistent "
            "user histories."
        )

        st.write(
            "Similarity scores from different methods "
            "should not be compared as equivalent "
            "relevance measurements."
        )