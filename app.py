"""Main web application for the Umbral Web knowledge system."""

from collections import Counter

import streamlit as st

from src.retrieval import RetrievalEngine
from src.recommender import RecommendationEngine
from src.chatbot import DocumentChatbot

from src.web.document_views import (
    CATEGORY_LABELS,
    render_documents,
    render_classification,
    render_search,
)

from src.web.recommendation_view import (
    render_recommendations,
)

from src.web.chatbot_view import (
    render_chatbot,
)


st.set_page_config(
    page_title="Umbral Web | Knowledge Hub",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def initialize_engines():
    """Initialize shared document infrastructure once."""

    retrieval = RetrievalEngine()

    recommender = RecommendationEngine(retrieval)

    chatbot = DocumentChatbot(retrieval)

    return retrieval, recommender, chatbot


def navigate_to(page):
    """Update the selected navigation destination."""

    st.session_state["navigation"] = page


def render_sidebar():
    """Display the application navigation."""

    with st.sidebar:

        st.title("◈ UMBRAL WEB")

        st.caption("KNOWLEDGE HUB")

        st.divider()

        page = st.radio(
            "Navigation",
            options=[
                "Overview",
                "Documents",
                "Classification",
                "Search",
                "Recommendations",
                "Assistant",
                "Knowledge Graph",
            ],
            label_visibility="collapsed",
            key="navigation",
        )

        st.divider()

        st.caption("Knowledge Management System")
        st.caption("Academic prototype")

    return page


def render_overview(retrieval):
    """Display the knowledge collection overview."""

    st.title("Knowledge overview")

    st.write(
        "Explore, connect, and reuse the collective "
        "knowledge of Umbral Web."
    )

    documents = retrieval.documents

    categories = Counter(
        document.category
        for document in documents
    )

    st.divider()

    first, second, third = st.columns(3)

    first.metric(
        "Documents",
        len(documents),
    )

    second.metric(
        "Knowledge categories",
        len(categories),
    )

    third.metric(
        "Validated engine tests (F03)",
        49,
    )

    st.subheader("Knowledge categories")

    columns = st.columns(3)

    category_descriptions = {
        "design_references": (
            "Visual hierarchy, interface motion, "
            "and modular composition."
        ),
        "creative_methods": (
            "Idea generation, proposal testing, "
            "and concept evaluation."
        ),
        "project_lessons": (
            "Experiences and lessons learned "
            "from previous projects."
        ),
    }

    for column, category in zip(
        columns,
        CATEGORY_LABELS,
    ):

        with column:

            with st.container(border=True):

                st.markdown(
                    f"**{CATEGORY_LABELS[category]}**"
                )

                st.metric(
                    "Documents",
                    categories.get(category, 0),
                )

                st.write(
                    category_descriptions[category]
                )

    st.divider()

    st.subheader("Explore the knowledge system")

    features = [
        (
            "Documents",
            "Browse the internal knowledge collection.",
            True,
        ),
        (
            "Classification",
            "Automatically identify document categories.",
            True,
        ),
        (
            "Search",
            "Retrieve documents related to your query.",
            True,
        ),
        (
            "Recommendations",
            "Discover related documents with explanations.",
            True,
        ),
        (
            "Assistant",
            "Ask questions using internal knowledge.",
            True,
        ),
        (
            "Knowledge Graph",
            "Explore relationships between knowledge concepts.",
            False,
        ),
    ]

    for start in range(0, len(features), 2):

        columns = st.columns(2)

        for column, feature in zip(
            columns,
            features[start:start + 2],
        ):

            title, description, available = feature

            with column:

                with st.container(border=True):

                    st.subheader(title)

                    st.write(description)

                    if available:

                        st.caption("Available")

                    else:

                        st.caption("Integration pending")

                    st.button(
                        f"Open {title}",
                        key=f"overview_{title}",
                        on_click=navigate_to,
                        args=(title,),
                    )

    st.caption(
        "Umbral Web is a fictional organization "
        "developed for an academic knowledge "
        "management project."
    )


def render_knowledge_graph():
    """Reserve the integration point for the knowledge graph."""

    st.title("Knowledge graph")

    st.write(
        "Explore the relationships between knowledge "
        "categories, concepts, and documents."
    )

    st.info(
        "The interactive knowledge graph is "
        "pending team integration."
    )


def main():
    """Run the web application."""

    retrieval, recommender, chatbot = (
        initialize_engines()
    )

    page = render_sidebar()

    if page == "Overview":

        render_overview(retrieval)

    elif page == "Documents":

        render_documents(retrieval)

    elif page == "Classification":

        render_classification()

    elif page == "Search":

        render_search(retrieval)

    elif page == "Recommendations":

        render_recommendations(recommender)

    elif page == "Assistant":

        render_chatbot(chatbot)

    elif page == "Knowledge Graph":

        render_knowledge_graph()


if __name__ == "__main__":
    main()