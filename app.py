"""UMBRAL WEB entry point and shared knowledge engines."""

import streamlit as st

from src.chatbot import DocumentChatbot
from src.recommender import RecommendationEngine
from src.retrieval import RetrievalEngine
from src.web.prototype_ui import render_prototype


st.set_page_config(page_title="Umbral Web | Knowledge Hub", layout="wide")


@st.cache_resource
def initialize_engines():
    """Share read-only engine resources across web sessions."""
    retrieval = RetrievalEngine()
    return retrieval, RecommendationEngine(retrieval), DocumentChatbot(retrieval)


def render_knowledge_graph():
    st.title("Knowledge graph")
    st.write("Explore the relationships between knowledge categories, concepts, and documents.")
    st.info("The interactive knowledge graph is pending team integration.")


def main():
    retrieval, recommender, chatbot = initialize_engines()
    page = render_prototype(retrieval, recommender, chatbot)

    if page == "Knowledge Graph":
        with st.container(key="umbral-native"):
            render_knowledge_graph()


if __name__ == "__main__":
    main()
