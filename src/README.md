# Automated document classification (Team member 3)

`classifier.py` assigns each Umbral Web document to one of the three agreed categories: `design_references`, `creative_methods` and `project_lessons`.

## How to run it

From the repository root:

```bash
pip install -r requirements.txt
python src/classifier.py
python src/classifier.py --model logreg
python src/classifier.py --save-evidence
python src/classifier.py --text "New text to classify"
python src/classifier.py --file path/to/new_document.txt
```

Naive Bayes is the default classification model.

The `--text` and `--file` arguments can be repeated to classify several new texts in one run.

## How it works

1. **Load.** The script reads `data/catalog.json` and opens each `.txt` file listed in the catalog. Document paths use `data/documents/`. Legacy paths using `datos/documentos/` remain supported for backward compatibility.

2. **Clean.** The header lines (company name, code, type, responsible department) and the title are removed. Fields such as "Type: Closeout report" or "Responsible department: Project Management" correspond directly to a category, so keeping them would let the model guess the label without reading the content. Only the body text is classified. The `category` and `suggested_use` fields are used as labels and to split the data, never as input text.

3. **Split.** The catalog's `suggested_use` field defines six training documents (two per category) and three test documents (UW03, UW06, UW09).

4. **TF-IDF.** `TfidfVectorizer` turns each text into a vector of word weights. A term scores high when it appears often in a document but rarely in the others. English stop words are removed and both single words and two-word phrases are used. The vocabulary is fitted only on the training documents, so the test documents do not influence it.

5. **Train.** A Multinomial Naive Bayes model learns which terms are typical of each category. Logistic Regression is available as an alternative. Both models give equal weight to each category.

6. **Classify.** The test documents are transformed with the same TF-IDF vocabulary, and the model returns a category and a probability for each one. The result is compared with the label in the catalog using accuracy, a per-category classification report, and a confusion matrix.

7. **New texts (optional).** Any text passed with `--text` or `--file` goes through the same cleaning and vectorization process and receives a predicted category.

As an additional check, the script runs a leave-one-out test: it trains with eight documents and classifies the remaining one, repeating the process for all nine documents.

## Results (test run)

| Model | Test set (UW03, UW06, UW09) | Leave-one-out (9 documents) |
| --- | --- | --- |
| Multinomial Naive Bayes | 3/3 | 7/9 |
| Logistic Regression | 3/3 | 5/9 |

Naive Bayes is kept as the default because it was more stable in the leave-one-out check.

The usual errors are UW02 (motion in an interface) and UW05 (short test of a proposal): they share vocabulary such as animation, transitions, prototype, and feedback with the closeout reports.

With only nine short documents, these results demonstrate that the pipeline works; they do not show how the model would perform on new documents of any kind.

The original classification results were reproduced during the project foundation and modularization phases.

## Evidence

The `--save-evidence` argument writes the following files to `evidences/classification/`:

- `run_<model>.txt`: full console output.
- `console_<model>.png`: the same output as an image.
- `predictions_<model>.csv`: test documents with actual category, predicted category, and probabilities.
- `new_texts_<model>.csv`: predictions for the texts passed with `--text` or `--file`.
- `confusion_matrix_<model>.png`: confusion matrix for the test set.

Historical evidence is preserved in the repository.

Running the classifier with `--save-evidence` may overwrite existing evidence files with the same names. Back up historical results before generating new evidence.

# Implementation of basic semantic search (Team member 4)

The original `interactive.py` implementation provides basic document retrieval using TF-IDF and cosine similarity.

The user enters a query, and the script displays up to three documents with positive similarity scores, ranked from highest to lowest similarity, with matching query terms highlighted.

The retrieval logic has been extracted into `retrieval.py` so that it can be reused by other system components.

Run the command-line interface from the repository root:

```bash
python src/interactive.py
```

The interface displays an informative message when no relevant documents are found.

Press Enter without entering a query to exit. Keyboard interruptions are also handled gracefully.

## Shared retrieval engine

`retrieval.py` provides a reusable document retrieval engine based on TF-IDF and cosine similarity.

The engine loads the document collection and builds the document index during initialization.

The `search()` method accepts a natural language query and returns ranked `SearchResult` objects, including the document and its similarity score.

The command-line interface in `interactive.py` uses this shared engine.

Future recommendation and chatbot components will reuse the same retrieval infrastructure.

### Main components

- `RetrievalEngine`: loads documents, builds the index, and performs retrieval.
- `SearchResult`: stores a retrieved document and its similarity score.
- `search(query, top_k=3)`: returns up to the requested number of documents with positive similarity scores.

### Example usage

From the repository root:

```python
from src.retrieval import RetrievalEngine

engine = RetrievalEngine()

results = engine.search(
    "How can we organize a session to generate design ideas?"
)

for result in results:
    print(
        result.document.doc_id,
        result.document.title,
        result.similarity,
    )
```

## Retrieval baseline

| Query topic | First result | Cosine similarity |
| --- | --- | --- |
| Design idea generation | UW04 | 0.200033 |
| Animation and navigation | UW08 | 0.125356 |
| Aula Clara project lessons | UW07 | 0.232856 |
| Unknown term | No results | N/A |

The retrieval rankings and similarity scores were preserved after extracting the shared engine.

These results constitute regression evidence for the existing retrieval implementation, not a formal evaluation of recommendation quality.

## Automated regression tests

From the repository root, with the virtual environment active, run:

```bash
python -m unittest discover -s tests -v
```

The tests verify document loading, retrieval rankings, baseline similarity scores, empty queries, unknown terms, result limits, invalid parameters, and similarity ordering.

| Test | Purpose |
| --- | --- |
| test_document_collection | Verify that all nine documents are loaded. |
| test_ideation_query | Preserve design ideation retrieval results. |
| test_animation_query | Preserve animation retrieval results. |
| test_aula_clara_query | Preserve Aula Clara retrieval results. |
| test_empty_query | Handle empty and whitespace-only queries. |
| test_unknown_query | Handle unknown query terms. |
| test_top_k | Enforce the requested result limit. |
| test_invalid_top_k | Reject invalid result limits. |
| test_similarity_order | Verify similarity ordering and valid scores. |

All nine automated tests passed during the modular foundation validation.

The classification models and command-line retrieval interface were also validated separately, with no observed functional regressions.
