"""UMBRAL WEB entry point and shared knowledge engines."""

import os
from pathlib import Path

import streamlit as st

from src.chatbot import DocumentChatbot
from src.recommender import RecommendationEngine
from src.retrieval import RetrievalEngine
from src.web.prototype_ui import render_prototype


st.set_page_config(
    page_title="Umbral Web | Knowledge Hub",
    page_icon=Path(__file__).resolve().parent / "static" / "brand" / "umbral-favicon.svg",
    layout="wide",
)


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
    graph_candidate = os.environ.get("UMBRAL_GRAPH_CANDIDATE") == "1"
    graph_release = os.environ.get("UMBRAL_GRAPH_RELEASE", "0" if graph_candidate else "1") == "1"
    page = render_prototype(retrieval, recommender, chatbot,
                            graph_candidate=graph_candidate, graph_release=graph_release)

    if page == "Knowledge Graph" and not (graph_candidate or graph_release):
        with st.container(key="umbral-native"):
            render_knowledge_graph()


if __name__ == "__main__":
    main()
