# Umbral Web

An academic knowledge management prototype for a fictional software company specializing in web design. It aims to retrieve references, creative methods, and lessons learned that help the team move beyond repeated solutions.

## Current contents

- `datos/documentos/`: nine fictional internal texts in UTF-8.
- `datos/catalogo.json`: the path, title, category, and suggested use of each text. Paths are relative to the project's root folder.

The company, projects, and observations in the documents are fictional. The texts are formatted as internal documentation and were prepared as test material.

## Categories

- `design_references`: ideas and criteria to guide a visual proposal.
- `creative_methods`: procedures for generating, testing, or reviewing concepts.
- `project_lessons`: reference materials and conclusions from previous work.

| Code | Document | Category |
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

## Team use

Team members 3 and 4 must read the `.txt` files; the catalog contains the labels for training and checking the classification. The category and the `suggested_use` field must not be included as part of the text being classified.

For classification, six training documents (two per category) and three test documents (one per category) are suggested and identified in the catalog. Fit TF-IDF and train the model using only the training documents; then classify the test documents. All nine texts can be queried in the search component.

Suggested initial queries:
- How can we organize a session to generate design ideas?
- What should we review to prevent animations from making navigation difficult?

These are queries to run, not results already obtained. The collection supports an initial demonstration; its size does not allow conclusions that the classifier will perform the same way on new documents of any kind.
