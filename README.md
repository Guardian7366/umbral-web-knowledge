# UMBRAL WEB

An academic knowledge management prototype for a fictional web design organization. The Streamlit app provides Overview, Documents, Classification, Search, Recommendations, Assistant and a Knowledge Graph entry.

Documents reads and downloads the nine original texts. Classification offers Multinomial Naive Bayes and Logistic Regression. Search ranks lexical matches. Recommendations supports TF-IDF and BGE from a document or explicit query. Assistant answers in English using passages from the collection.

This release includes the approved Knowledge Graph in 3D and text views and the four authorized Umbrely runtime files. Both features are enabled by default. See the [resource and third-party notices](docs/THIRD_PARTY_NOTICES.md).

## Requirements and startup

Use CPython 3.11 (validated on Windows with 3.11.9). Run from the supplied candidate root or the corresponding authorized revision.

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

Linux/macOS shell:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1
```

Open <http://127.0.0.1:8501>. Use `--server.port` if 8501 is occupied. The historical `/preview/` address is the same app with the Streamlit option `--server.baseUrlPath preview`. Static resources are enabled by `.streamlit/config.toml`. The running app needs no auxiliary service or frontend build.

### First semantic recommendation

Select **Related ideas** in Recommendations to initialize `BAAI/bge-small-en-v1.5`. FastEmbed obtains the quantized ONNX model from Hugging Face over HTTPS. Use a writable cache directory and set `FASTEMBED_CACHE_PATH` to choose its location. Keep the cache outside the repository and the static directory. A new process can reuse the files if the cache persists. `HF_HUB_OFFLINE=1` requires a usable copy. On a loading error the interface allows retry or an explicit switch to **Shared words**.

### Release and local review assets

- The release reads `src/web/graph_release.json` and verifies its approved hash. Set `UMBRAL_GRAPH_RELEASE=0` to disable the release graph. To review the historical private snapshot, place it at `src/web/graph_snapshot.json` and set `UMBRAL_GRAPH_CANDIDATE=1`. Explicitly setting `UMBRAL_GRAPH_RELEASE=1` takes precedence. To build the existing graph frontend, run `npm ci` then `npm run build` in `frontend/knowledge_graph`. Its lock file pins Three.js 0.184.0 and esbuild 0.25.12. The already compiled resources under `static/graph/` serve the application at runtime.
- The four approved files `umbrely-manifest.json`, `umbrely-neutral.png`, `umbrely-atlas.png` and `umbrely-expressions.png` are shipped in `static/umbrely-local/`. Idle and its pause control are enabled with the authorized artwork. Set `UMBRAL_UMBRELY_LOCAL=0` to disable the character for local diagnostics.

If resources fail to load, launch from the project root and check `.streamlit/config.toml`. If BGE cannot start, check the writable cache and HTTPS access. Use `python -m pip check` to review the Python environment.

## Project structure and tests

- `app.py` is the Streamlit entry point.
- `src/` contains the document engines and optional CLI tools.
- `src/web/` contains the interface adapters and component sources.
- `data/` contains the catalog and UTF-8 originals.
- `static/` holds fonts, marks and compiled browser assets.
- `frontend/knowledge_graph/` contains the source and build configuration.
- `tests/` uses standard-library unittest and runtime dependencies.
- `requirements-dev.txt` adds Matplotlib for classifier evidence charts and NetworkX for the contributor's standalone graph drawing. Install it before generating those charts with `src/classifier.py --save-evidence`.
- `docs/` and [src/README.md](src/README.md) provide academic and historical technical documentation. Historical captures and lab files belong to the development archive.

With the environment active:

```bash
python -m unittest discover -s tests -v
python -m pip check
```

The regression suite checks the approved graph, the runtime artwork and the handling of private preview data. Historical counts below refer to their original milestones.

## Document categories

- `design_references`: ideas and criteria to guide a visual proposal.
- `creative_methods`: procedures for generating, testing, or reviewing concepts.
- `project_lessons`: reference materials and conclusions from previous work.

## Document collection

| ID | Document | Category |
| --- | --- | --- |
| UW01 | Visual Hierarchy for Content-Heavy Pages | design_references |
| UW02 | Motion and Visual Feedback in an Interface | design_references |
| UW03 | Modular Composition for a Flexible Identity | design_references |
| UW04 | Brief Idea Generation Session | creative_methods |
| UW05 | Short Test of a Visual Proposal | creative_methods |
| UW06 | Concept Review Before Choosing a Direction | creative_methods |
| UW07 | Project Closeout for the Aula Clara Course Catalog | project_lessons |
| UW08 | Project Closeout for the Estudio Norte Portfolio | project_lessons |
| UW09 | Project Closeout for the Mesa Abierta Digital Menu | project_lessons |

## Optional command-line tools

The following commands assume that the virtual environment is active.

### Document classification

```bash
python src/classifier.py
```

Alternative classification model:

```bash
python src/classifier.py --model logreg
```

Classify new text:

```bash
python src/classifier.py --text "New text to classify"
```

### Document retrieval

```bash
python src/interactive.py
```

Suggested queries:

- How can we organize a session to generate design ideas?
- What should we review to prevent animations from making navigation difficult?
- What lessons were learned from the Aula Clara course catalog?

Press Enter without entering a query to exit.

If no relevant documents are found, the system displays an informative message.

## Baseline evaluation

| Model | Test set | Leave-one-out |
| --- | --- | --- |
| Multinomial Naive Bayes | 3/3 | 7/9 |
| Logistic Regression | 3/3 | 5/9 |

These results were reproduced locally during the project foundation phase.

Naive Bayes is the default classification model.

The catalog defines six training documents and three test documents. All nine documents are available for retrieval.

Category labels and dataset split metadata must not be included as classification input.

## Academic context

The company, projects, and observations described in the documents are fictional. The collection was created for academic testing and demonstration.

## Document recommendation system (F02)

The document recommendation system is implemented
and validated.

It supports:

- Recommendations based on a selected document.
- Recommendations based on the current search query.
- Cosine similarity scores.
- Shared relevant terms and recommendation explanations.
- Configurable result limits and similarity thresholds.

Run the recommendation interface:

```bash
python src/recommendation_cli.py
```

The complete automated regression suite now contains
29 tests: nine retrieval tests and 20 recommendation
tests.

All 29 tests passed during F02 validation.

See [F02 technical documentation](docs/F02-recommendation-system.md)
for the methodology, execution examples, validation
results, limitations, and evidence references.

## Document chatbot (F03)

The document-based chatbot is implemented and validated.

It supports:

- Natural language questions in English.
- Weighted content and title ranking.
- Vocabulary coverage validation.
- Extractive answers based on original document sentences.
- Supporting document sources.
- Abstention when relevant information is insufficient.

Run the chatbot:

```bash
python src/chatbot_cli.py
```

The chatbot passed 16 functional validation cases,
including ten answered questions, five abstentions,
and one empty input validation.

All nine source documents were represented in the
positive validation cases.

The complete automated regression suite contains
49 tests, all of which passed during F03 validation.

See [F03 technical documentation](docs/F03-document-chatbot.md)
for the methodology, validation examples, limitations,
and evidence references.
