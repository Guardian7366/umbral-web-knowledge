"""Document library, classification, and search web views."""

from __future__ import annotations

import streamlit as st

from src.classifier import (
    train,
    classify,
    split_documents,
    load_documents,
)


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


@st.cache_resource
def initialize_classifier(model_name: str):
    """Train a classifier using only the original training set."""

    documents = load_documents()

    training_documents, test_documents = (
        split_documents(documents)
    )

    vectorizer, model = train(
        training_documents,
        model_name,
    )

    return (
        vectorizer,
        model,
        len(training_documents),
        len(test_documents),
    )


def render_classification() -> None:
    """Classify text using the original classification models."""

    st.title("Document classification")

    st.write(
        "Automatically identify the most relevant "
        "knowledge category for a document."
    )

    algorithms = {
        "nb": "Naive Bayes",
        "logreg": "Logistic Regression",
    }

    with st.form("classification_form"):

        algorithm = st.selectbox(
            "Classification algorithm",
            options=list(algorithms.keys()),
            format_func=lambda value: algorithms[value],
        )

        document_text = st.text_area(
            "Document text",
            height=220,
            placeholder=(
                "Enter an English document or paragraph "
                "to classify..."
            ),
        )

        submitted = st.form_submit_button(
            "Classify document",
            type="primary",
        )

    if submitted:

        st.session_state.pop(
            "classification_result",
            None,
        )

        if not document_text.strip():

            st.warning(
                "Please enter some text to classify."
            )

            return

        vectorizer, model, training_count, test_count = (
            initialize_classifier(algorithm)
        )

        input_vector = vectorizer.transform(
            [document_text.strip()]
        )

        if input_vector.nnz == 0:

            st.warning(
                "The submitted text does not contain "
                "recognized classification vocabulary."
            )

            return

        predictions, _ = classify(
            [document_text.strip()],
            vectorizer,
            model,
        )

        st.session_state["classification_result"] = {
            "category": str(predictions[0]),
            "algorithm": algorithms[algorithm],
            "training_count": training_count,
            "test_count": test_count,
        }

    result = st.session_state.get(
        "classification_result"
    )

    if result:

        st.divider()

        st.subheader("Classification result")

        st.success(
            category_label(result["category"])
        )

        first, second, third = st.columns(3)

        first.metric(
            "Algorithm",
            result["algorithm"],
        )

        second.metric(
            "Training documents",
            result["training_count"],
        )

        third.metric(
            "Reserved test documents",
            result["test_count"],
        )

        st.caption(
            "This is a model prediction, not a "
            "guarantee of document relevance."
        )

    with st.expander("About classification"):

        st.write(
            "The classifier uses TF-IDF text features "
            "and the original Naive Bayes or Logistic "
            "Regression algorithm."
        )

        st.write(
            "Only the six original training documents "
            "are used to fit the selected classifier. "
            "The three test documents remain reserved."
        )

        st.write(
            "Submitted text is not added to the "
            "document collection or training set."
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