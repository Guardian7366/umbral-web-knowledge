"""Classification form and session-local results for Components v2."""

from html import escape
import logging
from uuid import uuid4

import streamlit as st

from src.classifier import build_model, classify, load_documents, split_documents, train
from src.web.chatbot_view import REVISION_KEY
from src.web.document_views import category_label


LOGGER = logging.getLogger(__name__)
METHODS = {
    "nb": ("Word patterns", "Multinomial Naive Bayes", "Word patterns checks which terms are typical of each category.", ("alpha", "fit_prior")),
    "logreg": ("Weighted signals", "Logistic Regression", "Weighted signals uses learned weights to choose a category for your text.", ("C", "max_iter", "class_weight")),
}
DESCRIPTIONS = {
    "design_references": "Principles and examples for making design choices.",
    "creative_methods": "Ways to generate, test and refine design ideas.",
    "project_lessons": "Observations and lessons from completed projects.",
}


@st.cache_resource
def initialize_classifier(model_name):
    """Reuse one fitted model per method, using the original partition."""
    training, testing = split_documents(load_documents())
    vectorizer, model = train(training, model_name)
    return vectorizer, model, len(training), len(testing)


def handle_classification_action(state, action):
    if not isinstance(action, dict) or state.get("navigation") != "Classification":
        return False
    if action.get("revision") != state[REVISION_KEY]:
        return action.get("kind") == "classify_text"
    kind = action.get("kind")
    if kind not in ("classify_text", "navigate"):
        return False
    text, method = action.get("classificationText"), action.get("classificationMethod")
    if not isinstance(text, str) or not isinstance(method, str) or method not in METHODS:
        return kind == "classify_text"

    previous = state.get("classification_draft")
    state["classification_draft"] = (text, method)
    if kind == "navigate":
        if previous != (text, method):
            state.pop("classification_result", None)
            state.pop("classification_notice", None)
        return False

    state[REVISION_KEY] = uuid4().hex
    state.pop("classification_result", None)
    state.pop("classification_notice", None)
    document = text.strip()
    if not document:
        state["classification_notice"] = ("empty", "Enter some text to classify.")
        return True

    try:
        vectorizer, model, training, testing = initialize_classifier(method)
        if vectorizer.transform([document]).nnz == 0:
            state["classification_notice"] = ("unknown", "No recognized terms. Try an English paragraph about the collection.")
            return True
        predictions, _ = classify([document], vectorizer, model)
        state["classification_result"] = {
            "category": str(predictions[0]), "algorithm": METHODS[method][1],
            "training_count": training, "test_count": testing,
        }
    except Exception:
        LOGGER.exception("Classification could not complete")
        state["classification_notice"] = ("error", "Couldn’t classify this text.")
    return True


def _details(method, result):
    _, algorithm, _, keys = METHODS[method]
    settings = build_model(method).get_params()
    values = ", ".join(f"{key}={settings[key]}" for key in keys)
    counts = (
        f'<p>{result["training_count"]} training documents</p><p>{result["test_count"]} reserved for testing</p>'
        if result else '<p>6 training documents · 3 reserved for testing</p>'
    )
    return (
        f'<div data-method-info="{method}"><strong>{algorithm}</strong>{counts}'
        f'<p>{escape(values)}</p><p>TF-IDF uses lowercase text, English stop words, one- and two-word terms, '
        'and sublinear term frequency.</p></div>'
    )


def render_classification(state):
    text, method = state.get("classification_draft", ("", "nb"))
    result = state.get("classification_result")
    notice = state.get("classification_notice")
    options = "".join(
        f'<label><input name="classification-method" type="radio" value="{key}"'
        f'{" checked" if key == method else ""}><span>{label}</span></label>'
        for key, (label, *_details_unused) in METHODS.items()
    )
    details = "".join(_details(key, result) for key in METHODS)
    panel = ""
    if result:
        category = result["category"]
        panel = f"""
            <section class="classification-tab" data-category="{escape(category)}" aria-labelledby="classification-category">
                <p class="classification-tab-label">Suggested category</p>
                <span class="classification-cant" aria-hidden="true"></span>
                <h2 id="classification-category">{escape(category_label(category))}</h2>
                <p class="classification-description">{escape(DESCRIPTIONS.get(category, ""))}</p>
            </section>
        """
    message = ""
    if notice:
        kind, description = notice
        retry = '<button type="submit" class="text-action" name="retry">Retry</button>' if kind == "error" else ""
        message = f'<p>{escape(description)}</p>{retry}'
    help_text = escape(METHODS[method][2])
    return f"""
        <section class="classification-workspace">
            <header class="classification-heading">
                <h1 id="page-title" tabindex="-1"><span class="classification-desktop-title">Classification</span><span class="classification-mobile-title">Classify a text</span></h1>
                <p>Give a piece of writing a category based on examples from the collection.</p>
            </header>
            <div class="classification-layout">
                <form class="classification-sheet">
                    <label for="classification-text">Your text</label>
                    <p id="classification-helper">Enter an English paragraph or document.</p>
                    <textarea id="classification-text" aria-describedby="classification-helper classification-message"
                        rows="6">{escape(text)}</textarea>
                    <fieldset aria-describedby="classification-method-help">
                        <legend>How to classify</legend><div class="classification-options">{options}</div>
                    </fieldset>
                    <p id="classification-method-help">{help_text}</p>
                    <div class="classification-submit">
                        <button type="submit" class="primary">Classify text</button>
                        <p class="classification-busy" role="status" hidden>Classifying…</p>
                    </div>
                    <div id="classification-message" data-state="{notice[0] if notice else ""}" role="status"
                        {"" if notice else "hidden"}>{message}</div>
                </form>
                <aside class="classification-result" aria-label="Classification result">
                    <div class="classification-tab-holder">{panel}</div>
                    <p class="classification-await">Your suggested category will appear here.</p>
                    <details class="classification-details">
                        <summary>Method details</summary>
                        {details}
                        <p>Your text stays out of the collection and the training set.</p>
                    </details>
                </aside>
            </div>
        </section>
    """, {"text": text, "method": method, "result": result, "notice": notice, "help": {key: row[2] for key, row in METHODS.items()}}
