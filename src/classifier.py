"""
Umbral Web - Automated document classification prototype (Team member 3).

Pipeline, organized in steps:
    1. Load the catalog and the sample documents (.txt) from the repository.
    2. Clean each text: drop the header block, which contains metadata
       (document type, responsible department) that would give away the label.
    3. Split the collection using the catalog's `suggested_use` field
       (6 training documents, 3 test documents).
    4. Vectorize the text with TF-IDF, fitting the vocabulary ONLY on the
       training documents.
    5. Train a simple classifier (Multinomial Naive Bayes by default, or
       Logistic Regression).
    6. Classify the test documents into the predefined categories and
       compare against the catalog labels.
    7. (Optional) Classify any new text passed with --text or --file.

Usage (from the repository root):
    python src/classifier.py
    python src/classifier.py --model logreg
    python src/classifier.py --text "We ran a short ideation session and sketched three alternatives."
    python src/classifier.py --save-evidence

The category and `suggested_use` fields are used only as labels and to split
the data; they are never part of the text being classified.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.naive_bayes import MultinomialNB

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "data" / "catalog.json"
EVIDENCE_DIR = REPO_ROOT / "evidencias" / "classification"

# Predefined categories (same names as data/catalog.json and the README).
CATEGORIES = ["design_references", "creative_methods", "project_lessons"]

# Header lines that carry metadata instead of content.
HEADER_PREFIXES = ("UMBRAL WEB", "Code:", "Type:", "Responsible department:")


@dataclass
class Document:
    doc_id: str
    title: str
    category: str
    split: str          # "training" or "test"
    path: Path
    text: str           # cleaned body text (what the model sees)


# ---------------------------------------------------------------------------
# Step 1 - Load the catalog and the documents
# ---------------------------------------------------------------------------
def resolve_document_path(relative: str) -> Path:
    """Return the path of a document listed in the catalog.

    The catalog uses the Spanish folder names (datos/documentos) while the
    repository uses data/documents; both are accepted so the script keeps
    working if either one is renamed later.
    """
    candidates = [
        REPO_ROOT / relative,
        REPO_ROOT / relative.replace("datos/documentos", "data/documents"),
        REPO_ROOT / relative.replace("data/documents", "datos/documentos"),
        REPO_ROOT / "data" / "documents" / Path(relative).name,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Document not found for catalog entry: {relative}")


def load_documents(catalog_path: Path = CATALOG_PATH) -> list[Document]:
    with open(catalog_path, encoding="utf-8") as fh:
        catalog = json.load(fh)

    documents = []
    for entry in catalog:
        path = resolve_document_path(entry["file"])
        raw_text = path.read_text(encoding="utf-8")
        documents.append(
            Document(
                doc_id=entry["id"],
                title=entry["title"],
                category=entry["category"],
                split=entry["suggested_use"],
                path=path,
                text=clean_text(raw_text, entry["title"]),
            )
        )
    return documents


# ---------------------------------------------------------------------------
# Step 2 - Clean the text
# ---------------------------------------------------------------------------
def clean_text(raw_text: str, title: str | None = None) -> str:
    """Remove the header block (company name, code, type, department).

    "Type: Design note" or "Responsible department: Project Management" map
    one-to-one to the category, so keeping them would let the model
    'cheat'. The title is also removed so the model learns from the body.
    """
    body_lines = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(HEADER_PREFIXES):
            continue
        if title and stripped == title:
            continue
        body_lines.append(stripped)
    return " ".join(body_lines)


# ---------------------------------------------------------------------------
# Step 3 - Split into training and test sets
# ---------------------------------------------------------------------------
def split_documents(documents: list[Document]) -> tuple[list[Document], list[Document]]:
    train = [d for d in documents if d.split == "training"]
    test = [d for d in documents if d.split == "test"]
    return train, test


# ---------------------------------------------------------------------------
# Step 4 - TF-IDF vectorization
# ---------------------------------------------------------------------------
def build_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        lowercase=True,
        stop_words="english",   # drop words like "the", "and", "must"
        ngram_range=(1, 2),     # single words and two-word phrases
        sublinear_tf=True,      # dampen very repeated words
    )


# ---------------------------------------------------------------------------
# Step 5 - Train a simple classifier
# ---------------------------------------------------------------------------
def build_model(name: str):
    if name == "nb":
        return MultinomialNB(alpha=0.1, fit_prior=False)
    if name == "logreg":
        return LogisticRegression(C=10.0, max_iter=1000, class_weight="balanced")
    raise ValueError(f"Unknown model: {name}")


MODEL_NAMES = {"nb": "Multinomial Naive Bayes", "logreg": "Logistic Regression"}


def train(train_docs: list[Document], model_name: str):
    vectorizer = build_vectorizer()
    X_train = vectorizer.fit_transform([d.text for d in train_docs])  # fit ONLY on training
    y_train = [d.category for d in train_docs]
    model = build_model(model_name)
    model.fit(X_train, y_train)
    return vectorizer, model


def top_terms_per_category(vectorizer, model, n: int = 8) -> dict[str, list[str]]:
    """Most influential terms per category (helps explain the decisions)."""
    terms = np.array(vectorizer.get_feature_names_out())
    weights = model.feature_log_prob_ if hasattr(model, "feature_log_prob_") else model.coef_
    result = {}
    for idx, category in enumerate(model.classes_):
        row = weights[idx]
        if hasattr(model, "feature_log_prob_"):
            # Naive Bayes: how much more likely the term is in this class than in the others
            row = row - np.delete(weights, idx, axis=0).mean(axis=0)
        result[category] = terms[np.argsort(row)[::-1][:n]].tolist()
    return result


# ---------------------------------------------------------------------------
# Step 6 - Classify documents
# ---------------------------------------------------------------------------
def classify(texts: list[str], vectorizer, model) -> tuple[list[str], np.ndarray]:
    X = vectorizer.transform(texts)
    return list(model.predict(X)), model.predict_proba(X)


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------
def line(char: str = "-", width: int = 78) -> str:
    return char * width


def run(model_name: str, extra_texts: list[str], save_evidence: bool) -> int:
    out: list[str] = []

    def emit(text: str = "") -> None:
        print(text)
        out.append(text)

    emit(line("="))
    emit("UMBRAL WEB - Automated document classification")
    emit(f"Model: {MODEL_NAMES[model_name]} | Vectorizer: TF-IDF (unigrams + bigrams)")
    emit(line("="))

    # Step 1-2
    documents = load_documents()
    emit(f"\n[Step 1] Loaded {len(documents)} documents from {CATALOG_PATH.relative_to(REPO_ROOT)}")
    for d in documents:
        emit(f"  {d.doc_id}  {d.split:<8}  {d.category:<18}  {d.path.relative_to(REPO_ROOT)}")
    emit("\n[Step 2] Header removed (code, type, department, title); body text kept.")
    emit(f"  Example ({documents[0].doc_id}): \"{documents[0].text[:110]}...\"")

    # Step 3
    train_docs, test_docs = split_documents(documents)
    emit(f"\n[Step 3] Training: {', '.join(d.doc_id for d in train_docs)}")
    emit(f"         Test:     {', '.join(d.doc_id for d in test_docs)}")

    # Step 4-5
    vectorizer, model = train(train_docs, model_name)
    emit(f"\n[Step 4] TF-IDF vocabulary fitted on training set: {len(vectorizer.vocabulary_)} terms")
    emit(f"[Step 5] Model trained on {len(train_docs)} documents, classes: {[str(c) for c in model.classes_]}")
    emit("  Most characteristic terms per category:")
    for category, terms in top_terms_per_category(vectorizer, model).items():
        emit(f"    {category:<18} {', '.join(terms)}")

    # Step 6
    predictions, probabilities = classify([d.text for d in test_docs], vectorizer, model)
    emit("\n[Step 6] Classification of the test documents")
    emit(line())
    header = f"{'ID':<5} {'Title':<44} {'Actual':<18} {'Predicted':<18} {'Prob.':>5}  OK"
    emit(header)
    emit(line())
    rows = []
    for doc, pred, probs in zip(test_docs, predictions, probabilities):
        conf = probs.max()
        ok = "yes" if pred == doc.category else "NO"
        emit(f"{doc.doc_id:<5} {doc.title[:43]:<44} {doc.category:<18} {pred:<18} {conf:>5.2f}  {ok}")
        rows.append({
            "id": doc.doc_id,
            "title": doc.title,
            "actual_category": doc.category,
            "predicted_category": pred,
            **{f"prob_{c}": round(float(p), 4) for c, p in zip(model.classes_, probs)},
            "correct": pred == doc.category,
        })
    emit(line())

    y_true = [d.category for d in test_docs]
    acc = accuracy_score(y_true, predictions)
    emit(f"Accuracy on test set: {acc:.2f} ({sum(r['correct'] for r in rows)}/{len(rows)})")
    emit("\nPer-category report:")
    emit(classification_report(y_true, predictions, labels=CATEGORIES, zero_division=0))
    cm = confusion_matrix(y_true, predictions, labels=CATEGORIES)
    emit("Confusion matrix (rows = actual, columns = predicted):")
    emit(" " * 20 + "".join(f"{c[:14]:>16}" for c in CATEGORIES))
    for c, r in zip(CATEGORIES, cm):
        emit(f"{c:<20}" + "".join(f"{v:>16}" for v in r))
    # Extra check: leave-one-out over the 9 documents (train on 8, predict 1)
    loo_hits = []
    for held_out in documents:
        rest = [d for d in documents if d is not held_out]
        v, m = train(rest, model_name)
        pred = classify([held_out.text], v, m)[0][0]
        loo_hits.append((held_out.doc_id, held_out.category, pred))
    n_ok = sum(a == p for _, a, p in loo_hits)
    emit(f"\n[Extra] Leave-one-out check over all 9 documents: {n_ok}/{len(loo_hits)} correct")
    for doc_id, actual, pred in loo_hits:
        if actual != pred:
            emit(f"  {doc_id}: actual {actual}, predicted {pred}")

    emit("\nNote: with 9 documents this is a demonstration, not a measure of how the")
    emit("model will perform on new documents of any kind.")

    # Step 7 - new texts
    new_rows = []
    if extra_texts:
        emit("\n[Step 7] Classification of new texts")
        emit(line())
        preds, probs_all = classify([clean_text(t) for t in extra_texts], vectorizer, model)
        for i, (text, pred, probs) in enumerate(zip(extra_texts, preds, probs_all), 1):
            short = text if len(text) <= 70 else text[:67] + "..."
            emit(f"  Text {i}: \"{short}\"")
            detail = ", ".join(f"{c}={p:.2f}" for c, p in zip(model.classes_, probs))
            emit(f"    -> {pred}   ({detail})")
            new_rows.append({"text": text, "predicted_category": pred,
                             **{f"prob_{c}": round(float(p), 4) for c, p in zip(model.classes_, probs)}})

    if save_evidence:
        save_outputs(model_name, out, rows, new_rows, cm)
    return 0


def save_outputs(model_name, out_lines, rows, new_rows, cm) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / f"run_{model_name}.txt").write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    with open(EVIDENCE_DIR / f"predictions_{model_name}.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    if new_rows:
        with open(EVIDENCE_DIR / f"new_texts_{model_name}.csv", "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(new_rows[0].keys()))
            writer.writeheader()
            writer.writerows(new_rows)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 5))
        ax.imshow(cm, cmap="Blues", vmin=0, vmax=max(1, cm.max()))
        ax.set_xticks(range(len(CATEGORIES)), CATEGORIES, rotation=20, ha="right")
        ax.set_yticks(range(len(CATEGORIES)), CATEGORIES)
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, cm[i, j], ha="center", va="center",
                        color="white" if cm[i, j] else "black", fontsize=14)
        ax.set_xlabel("Predicted category")
        ax.set_ylabel("Actual category")
        ax.set_title(f"Confusion matrix - {MODEL_NAMES[model_name]}")
        fig.tight_layout()
        fig.savefig(EVIDENCE_DIR / f"confusion_matrix_{model_name}.png", dpi=150)
        plt.close(fig)

        # Console output rendered as an image (screenshot-style evidence)
        lines = out_lines
        fig = plt.figure(figsize=(9.5, 0.17 * len(lines) + 0.4))
        fig.patch.set_facecolor("#1e1e1e")
        fig.text(0.01, 0.995, "\n".join(lines), family="monospace", fontsize=7.5,
                 color="#e6e6e6", va="top", ha="left")
        fig.savefig(EVIDENCE_DIR / f"console_{model_name}.png", dpi=150, facecolor=fig.get_facecolor())
        plt.close(fig)
    except ImportError:
        print("matplotlib not installed: images skipped.")

    print(f"\nEvidence saved in {EVIDENCE_DIR.relative_to(REPO_ROOT)}/")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Umbral Web TF-IDF document classifier")
    parser.add_argument("--model", choices=["nb", "logreg"], default="nb",
                        help="nb = Multinomial Naive Bayes (default), logreg = Logistic Regression")
    parser.add_argument("--text", action="append", default=[],
                        help="New text to classify (can be repeated)")
    parser.add_argument("--file", action="append", default=[],
                        help="Path of a .txt file to classify (can be repeated)")
    parser.add_argument("--save-evidence", action="store_true",
                        help="Save console output, CSV and confusion matrix in evidencias/classification/")
    args = parser.parse_args(argv)

    extra = list(args.text)
    for f in args.file:
        extra.append(Path(f).read_text(encoding="utf-8"))
    return run(args.model, extra, args.save_evidence)


if __name__ == "__main__":
    sys.exit(main())
