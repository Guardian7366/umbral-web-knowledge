# Umbral Web

An academic knowledge management prototype for a
fictional software company specializing in web design.

The system aims to retrieve references, creative methods,
and lessons learned that help the team move beyond
repeated solutions.

## Project status

The initial prototype includes:

- A repository of nine fictional internal documents.
- Automated document classification using TF-IDF.
- Multinomial Naive Bayes and Logistic Regression models.
- Basic document retrieval using cosine similarity.
- A conceptual knowledge graph and knowledge lifecycle.
- Historical classification and search evidence.

The project is being prepared for its next development
phase, which will include recommendations, a chatbot,
an interactive knowledge graph, and web deployment.

## Project structure

- `data/documents/`: internal documents in UTF-8.
- `data/catalog.json`: document metadata and categories.
- `src/classifier.py`: automated document classification.
- `src/interactive.py`: basic document retrieval.
- `src/README.md`: technical documentation.
- `docs/`: knowledge lifecycle and ontology diagrams.
- `evidences/`: historical execution evidence.
- `requirements.txt`: direct Python dependencies.

## Document categories

- `design_references`: ideas and criteria to guide
  a visual proposal.
- `creative_methods`: procedures for generating,
  testing, or reviewing concepts.
- `project_lessons`: reference materials and conclusions
  from previous work.

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

## Requirements

- Python 3.11 (validated locally with Python 3.11.9).
- Dependencies listed in `requirements.txt`.

## Installation

Clone the repository:

```bash
git clone https://github.com/Guardian7366/umbral-web-knowledge.git
cd umbral-web-knowledge
```

Create a virtual environment:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

On Linux or macOS:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

## Running the prototype

The following commands assume that the virtual
environment is active.

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

## Baseline evaluation

| Model | Test set | Leave-one-out |
| --- | --- | --- |
| Multinomial Naive Bayes | 3/3 | 7/9 |
| Logistic Regression | 3/3 | 5/9 |

These results were reproduced locally during the
project foundation phase.

Naive Bayes is the default classification model.

The catalog defines six training documents and three
test documents. All nine documents are available
for retrieval.

Category labels and dataset split metadata must not
be included as classification input.

## Limitations

- The document collection contains only nine texts.
- Classification results do not establish generalization
  to larger or unseen document collections.
- Document retrieval is based on TF-IDF and cosine
  similarity rather than contextual embeddings.
- The current document collection is written in English.
- The existing prototype uses a command-line interface.

## Technical documentation

See [src/README.md](src/README.md) for details about
classification, retrieval, and historical evidence.

## Academic context

The company, projects, and observations described
in the documents are fictional. The collection was
created for academic testing and demonstration.
