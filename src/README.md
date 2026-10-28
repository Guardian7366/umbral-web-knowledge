# Automated document classification (Team member 3)

`classifier.py` assigns each Umbral Web document to one of the three agreed categories: `design_references`, `creative_methods` and `project_lessons`.

## How to run it

From the repository root:

```bash
pip install -r requirements.txt
python src/classifier.py                      # Naive Bayes (default)
python src/classifier.py --model logreg       # Logistic Regression
python src/classifier.py --save-evidence      # also writes evidencias/classification/
python src/classifier.py --text "New text to classify"
python src/classifier.py --file path/to/new_document.txt
```

`--text` and `--file` can be repeated to classify several new texts in one run.

## How it works

1. **Load.** The script reads `data/catalog.json` and opens each `.txt` listed there. The catalog stores paths as `datos/documentos/...`, while the folder is `data/documents/`; the script accepts both.
2. **Clean.** The header lines (company name, code, type, responsible department) and the title are removed. Fields such as "Type: Closeout report" or "Responsible department: Project Management" correspond directly to a category, so keeping them would let the model guess the label without reading the content. Only the body text is classified. The `category` and `suggested_use` fields are used as labels and to split the data, never as input text.
3. **Split.** The catalog's `suggested_use` field defines 6 training documents (two per category) and 3 test documents (UW03, UW06, UW09).
4. **TF-IDF.** `TfidfVectorizer` turns each text into a vector of word weights. A term scores high when it appears often in a document but rarely in the others. English stop words are removed and both single words and two-word phrases are used. The vocabulary is fitted **only on the training documents**, so the test documents do not influence it.
5. **Train.** A Multinomial Naive Bayes model learns which terms are typical of each category. Logistic Regression is available as an alternative. Both models give equal weight to each category.
6. **Classify.** The test documents are transformed with the same TF-IDF vocabulary, and the model returns a category and a probability for each one. The result is compared with the label in the catalog (accuracy, per-category report and confusion matrix).
7. **New texts (optional).** Any text passed with `--text` or `--file` goes through the same cleaning and vectorization and receives a predicted category.

As an additional check, the script runs a leave-one-out test: it trains with 8 documents and classifies the remaining one, repeating the process for all 9.

## Results (test run)

| Model | Test set (UW03, UW06, UW09) | Leave-one-out (9 documents) |
| --- | --- | --- |
| Multinomial Naive Bayes | 3/3 | 7/9 |
| Logistic Regression | 3/3 | 5/9 |

Naive Bayes is kept as the default because it was more stable in the leave-one-out check. The usual errors are UW02 (motion in an interface) and UW05 (short test of a proposal): they share vocabulary such as *animation*, *transitions*, *prototype* and *feedback* with the closeout reports.

With only nine short documents, these results demonstrate that the pipeline works; they do not show how the model would perform on new documents of any kind.

## Evidence

`--save-evidence` writes the following to `evidencias/classification/`:

- `run_<model>.txt`: full console output.
- `console_<model>.png`: the same output as an image.
- `predictions_<model>.csv`: test documents with actual category, predicted category and probabilities.
- `new_texts_<model>.csv`: predictions for the texts passed with `--text` or `--file`.
- `confusion_matrix_<model>.png`: confusion matrix for the test set.
