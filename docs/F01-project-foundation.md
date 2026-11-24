# F01 - Project Foundation

## Objective

Prepare the existing Umbral Web prototype for the final
development phase by validating its original components,
standardizing the repository, and extracting reusable
document retrieval infrastructure.

## Original baseline

- Base commit: a69c6c0
- Original branch: main
- Work branch: feature/f01-project-foundation

## Validated environment

| Component | Version |
| --- | --- |
| Python | 3.11.9 |
| scikit-learn | 1.9.1 |
| NumPy | 2.4.6 |
| Matplotlib | 3.11.2 |
| SciPy | 1.17.1 |

The Python environment was validated locally on Windows.
No dependency conflicts were reported by pip check.

## Completed activities

- F01.1: Original project preservation.
- F01.2: Local environment preparation.
- F01.3: Document collection validation.
- F01.4: Classification model validation.
- F01.5: Document retrieval validation.
- F01.6: Project standardization.
- F01.7: Modular retrieval infrastructure.
- F01.8: Technical closure documentation.

## Preserved components

- Original fictional company context.
- All nine original documents.
- Document identifiers and categories.
- Training and test assignments.
- Original classification algorithms.
- Knowledge lifecycle and ontology diagrams.
- Historical execution evidence.

## Implemented changes

### Standardization

Commit: ef10af5

- Standardized document paths.
- Unified evidence directory references.
- Pinned direct dependency versions.
- Updated project documentation.

### Modularization

Commit: e57a632

- Created src/retrieval.py.
- Extracted the shared retrieval engine.
- Adapted the command-line search interface.
- Added nine automated regression tests.
- Updated general and technical documentation.

## Classification validation

| Metric | Naive Bayes | Logistic Regression |
| --- | --- | --- |
| Documents loaded | 9 | 9 |
| Training documents | 6 | 6 |
| Test documents | 3 | 3 |
| TF-IDF vocabulary | 742 | 742 |
| Accuracy | 1.00 | 1.00 |
| Macro precision | 1.00 | 1.00 |
| Macro recall | 1.00 | 1.00 |
| Macro F1-score | 1.00 | 1.00 |
| Leave-one-out | 7/9 | 5/9 |

Naive Bayes remains the default classification model.

The perfect test-set metrics are based on only three
documents and do not establish generalization to larger
or unseen document collections.

## Retrieval validation

| Query topic | First result | Cosine similarity |
| --- | --- | --- |
| Design idea generation | UW04 | 0.200033 |
| Animation and navigation | UW08 | 0.125356 |
| Aula Clara project lessons | UW07 | 0.232856 |
| Unknown term | No results | N/A |

The original rankings and similarity scores were
preserved after modularization.

## Automated tests

Nine regression tests were executed successfully.

Result: 9/9 passed.

Observed execution time: 0.012 seconds.

The tests cover:

- Document loading.
- Baseline retrieval rankings.
- Baseline similarity scores.
- Empty queries.
- Unknown terms.
- Result limits.
- Invalid result limits.
- Similarity ordering.

No functional regressions were observed in the
executed classification and retrieval tests.

## Current limitations

- The document collection contains only nine documents.
- Retrieval uses TF-IDF rather than contextual embeddings.
- Documents are written in English.
- The current interface operates through the command line.
- Direct dependencies are pinned, but transitive
  dependencies are not fully locked.
- Deployment compatibility has not yet been validated.

## Next development phases

- F02: Document recommendation system.
- F03: Document-based chatbot.
- F04: Web interface and component integration.
- F05: Prototype deployment.
- F06: Technical handover.

## Conclusion

The original prototype has been successfully validated
and modularized.

The shared retrieval engine provides a reusable
foundation for the upcoming recommendation system,
chatbot, and web interface.

The project is ready to proceed to F02 once the final
repository checks are completed.