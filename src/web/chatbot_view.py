"""Session-local submission and response handling for the document assistant."""

import logging
from uuid import uuid4


LOGGER = logging.getLogger(__name__)
HISTORY_KEY = "assistant_history"
REVISION_KEY = "umbral_event_revision"
PAGES = (
    "Overview", "Documents", "Classification", "Search",
    "Recommendations", "Assistant", "Knowledge Graph",
)
EXAMPLE_QUESTIONS = (
    "How can we organize a session to generate design ideas?",
    "How should the team test a visual proposal before development?",
)


def handle_action(state, action, chatbot, *, answer_question=None):
    """Consume a rendered revision once, even if its event is replayed."""
    if not isinstance(action, dict) or action.get("revision") != state[REVISION_KEY]:
        return

    answer_question = answer_question or _answer
    kind = action.get("kind")
    page = state["navigation"]
    history = state[HISTORY_KEY]

    if kind == "navigate" and action.get("page") in PAGES:
        state[REVISION_KEY] = uuid4().hex
        state["navigation"] = action["page"]
        return

    if kind == "clear" and page == "Assistant":
        state[REVISION_KEY] = uuid4().hex
        history.clear()
        return

    if kind == "retry" and page == "Assistant":
        turn = action.get("turn")
        if type(turn) is int and 0 <= turn < len(history) // 2:
            user, answer = history[turn * 2:turn * 2 + 2]
            if answer["status"] == "error":
                state[REVISION_KEY] = uuid4().hex
                answer_question(chatbot, user["content"], answer)
        return

    if kind != "submit" or page not in ("Overview", "Assistant"):
        return
    text = action.get("text")
    if not isinstance(text, str):
        return
    question = text.strip()
    if page == "Assistant" and not question:
        return

    state[REVISION_KEY] = uuid4().hex
    state["navigation"] = "Assistant"
    if question:
        answer = {"role": "assistant", "status": "processing"}
        history.extend(({"role": "user", "content": question}, answer))
        answer_question(chatbot, question, answer)


def _answer(chatbot, question, answer):
    answer["status"] = "processing"
    try:
        response = chatbot.ask(question)
    except Exception:
        LOGGER.exception("Document assistant could not complete the turn")
        answer["status"] = "error"
    else:
        answer.update(status="complete", response=response)
