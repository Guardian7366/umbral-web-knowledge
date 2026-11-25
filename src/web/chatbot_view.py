"""Conversational web interface for the document chatbot."""

from __future__ import annotations

import streamlit as st

from src.web.document_views import category_label


HISTORY_KEY = "assistant_history"


EXAMPLE_QUESTIONS = (
    "How can we organize a session to generate design ideas?",
    "How should the team test a visual proposal before development?",
    "What lessons were learned from the Aula Clara course catalog?",
    "What changes were made to the Estudio Norte portfolio?",
)


def clear_conversation() -> None:
    """Remove the current session's conversation."""

    st.session_state[HISTORY_KEY] = []


def append_response(chatbot, question: str) -> None:
    """Process a question and store its structured response."""

    question = question.strip()

    if not question:
        return

    response = chatbot.ask(question)

    st.session_state[HISTORY_KEY].append(
        {
            "role": "user",
            "content": question,
        }
    )

    st.session_state[HISTORY_KEY].append(
        {
            "role": "assistant",
            "response": response,
        }
    )


def render_assistant_response(
    response,
    chatbot,
    message_index: int,
) -> None:
    """Display an answer and its supporting document sources."""

    st.write(response.answer)

    if not response.answered:

        st.caption(
            "No supporting document was retrieved."
        )

        return

    st.markdown("**Supporting sources**")

    document_by_id = {
        document.doc_id: document
        for document in chatbot.retrieval.documents
    }

    for source in response.sources:

        with st.expander(
            f"{source.document_id} - {source.title}"
        ):

            st.caption(
                category_label(source.category)
            )

            st.caption(
                f"Document similarity: "
                f"{source.similarity:.6f}"
            )

            fragments = [
                fragment
                for fragment in response.fragments
                if fragment.document_id == source.document_id
            ]

            st.markdown(
                "**Extracted source fragments**"
            )

            for fragment in fragments:

                st.write(fragment.text)

            document = document_by_id.get(
                source.document_id
            )

            if document is not None:

                st.divider()

                st.download_button(
                    label="Download source document",
                    data=document.path.read_bytes(),
                    file_name=document.path.name,
                    mime="text/plain",
                    key=(
                        f"assistant_download_"
                        f"{message_index}_"
                        f"{source.document_id}"
                    ),
                )

    st.caption(
        f"Extracted sentences: "
        f"{len(response.fragments)}"
    )


def render_chatbot(chatbot) -> None:
    """Display the conversational knowledge assistant."""

    st.title("Knowledge assistant")

    st.write(
        "Ask questions about the internal "
        "Umbral Web document collection."
    )

    if HISTORY_KEY not in st.session_state:

        st.session_state[HISTORY_KEY] = []

    first, second = st.columns([3, 1])

    with first:

        st.caption(
            "Document-based answers | English questions"
        )

    with second:

        st.button(
            "Clear conversation",
            on_click=clear_conversation,
            key="clear_assistant_history",
        )

    st.info(
        "The assistant answers using internal document "
        "fragments. Each question is processed "
        "independently."
    )

    history = st.session_state[HISTORY_KEY]

    if not history:

        with st.chat_message("assistant"):

            st.write(
                "Hello! I am the Umbral Web knowledge "
                "assistant. Ask me about design references, "
                "creative methods, or lessons learned "
                "from previous projects."
            )

        st.markdown("**Try an example question**")

        columns = st.columns(2)

        for index, question in enumerate(
            EXAMPLE_QUESTIONS
        ):

            with columns[index % 2]:

                if st.button(
                    question,
                    key=f"assistant_example_{index}",
                ):

                    with st.spinner(
                        "Retrieving internal knowledge..."
                    ):

                        append_response(
                            chatbot,
                            question,
                        )

                    st.rerun()

    for index, message in enumerate(history):

        role = message["role"]

        with st.chat_message(role):

            if role == "user":

                st.write(
                    message["content"]
                )

            else:

                render_assistant_response(
                    message["response"],
                    chatbot,
                    index,
                )

    question = st.chat_input(
        "Ask a question in English..."
    )

    if question:

        with st.spinner(
            "Retrieving internal knowledge..."
        ):

            append_response(
                chatbot,
                question,
            )

        st.rerun()