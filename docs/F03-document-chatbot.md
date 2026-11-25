# F03 - Document-Based Chatbot

## Objective

Implement a chatbot capable of answering natural
language questions using the internal Umbral Web
document collection.

The chatbot retrieves relevant information,
constructs extractive answers, identifies supporting
sources, and abstains when insufficient relevant
information is available.

## Development baseline

- Base commit: 1b6a634
- Work branch: feature/f03-document-chatbot
- Document collection: 9 documents
- Existing automated tests: 29
- Final chatbot version: 2

## Implemented components

| File | Responsibility |
| --- | --- |
| src/chatbot.py | Document-based chatbot engine |
| src/chatbot_cli.py | Command-line conversation interface |
| tests/test_chatbot.py | Automated chatbot tests |
| evidences/chatbot/functional_validation.txt | Functional validation evidence |
| evidences/chatbot/automated_tests.txt | Automated regression evidence |

The original classification, retrieval, and
recommendation modules remain unchanged.

## Technical approach

The chatbot uses an extractive question-answering
approach rather than an external generative language
model.

It reuses the TF-IDF infrastructure implemented
during F01.

No additional Python dependencies, external APIs,
API keys, or paid language models are required.

## Processing pipeline

1. Receive a natural language question.
2. Validate the question and vocabulary coverage.
3. Retrieve candidate documents.
4. Rank candidates using content and title features.
5. Detect the question's basic intent.
6. Select a consecutive window of relevant sentences.
7. Construct an extractive answer.
8. Return the answer and supporting document sources.

If the retrieval criteria are not satisfied, the
chatbot returns an informative abstention message.

## Document ranking

Candidate documents are ranked using a weighted
combination of four factors.

| Ranking factor | Weight |
| --- | --- |
| Content cosine similarity | 0.40 |
| Title cosine similarity | 0.25 |
| Document vocabulary coverage | 0.20 |
| Title vocabulary coverage | 0.15 |

These weights are heuristic design parameters.

They were selected during development and have not
been calibrated through an independent relevance
evaluation.

The document similarity displayed to the user is
the original content cosine similarity, not the
combined ranking score.

## Question intent

The chatbot uses general lexical rules to identify
basic question types.

| Intent | Prioritized information |
| --- | --- |
| Procedure | Instructions and sequences |
| Lessons | Conclusions and lessons learned |
| Changes | Adjustments and modifications |
| Reason | Explanations and justifications |
| General | Relevant document content |

Intent cues influence sentence window selection.

The implementation does not contain predefined
answers linked to specific validation questions.

## Answer construction

Documents are divided into original sentences.

Each sentence is represented using the existing
TF-IDF vocabulary and compared with the question.

The selection process considers sentence similarity
and intent-related vocabulary.

A consecutive sentence window is selected to
preserve contextual continuity.

Answers contain original document sentences rather
than newly generated factual statements.

Supporting sources include the document identifier,
title, category, and original cosine similarity.

## Configurable parameters

| Parameter | Default |
| --- | --- |
| max_documents | 1 |
| max_sentences | 7 |
| min_document_similarity | 0.03 |
| min_sentence_similarity | 0.05 |
| min_query_coverage | 0.50 |
| min_matched_terms | 2 |

The implementation additionally requires candidate
document vocabulary coverage of at least 0.35.

Similarity and vocabulary coverage thresholds are
heuristic parameters.

Contextual sentences within the selected window
may have individual similarity scores below the
minimum sentence similarity threshold.

## Version history

### Version 1

The initial implementation used document cosine
similarity and independently selected relevant
sentences.

Initial functional validation produced eight
satisfactory outcomes across ten cases, based on
expected sources and abstention behavior.

Two problems were identified:

- C04 retrieved UW01 instead of UW05 when asked
  about testing a visual proposal.
- C08 returned restaurant menu pricing information
  when asked about Bitcoin.

Several answers also omitted relevant procedural
steps or project conclusions.

### Version 2

The chatbot was improved through:

- Weighted document and title ranking.
- Vocabulary coverage validation.
- Minimum matched-term requirements.
- Basic question intent detection.
- Consecutive sentence window selection.
- Increased contextual sentence limits.

All ten original cases subsequently produced the
expected functional behavior.

Six additional cases were also validated.

## Functional validation

| Case | Topic | Expected result | Observed result |
| --- | --- | --- | --- |
| C01 | Design idea generation | UW04 | Passed |
| C02 | Animation and navigation | UW08 or UW02 | UW08 |
| C03 | Aula Clara lessons | UW07 | Passed |
| C04 | Visual proposal testing | UW05 | Passed |
| C05 | Estudio Norte changes | UW08 | Passed |
| C06 | Visual hierarchy | UW01 | Passed |
| C07 | Capital of France | Abstention | Passed |
| C08 | Bitcoin price | Abstention | Passed |
| C09 | Unknown vocabulary | Abstention | Passed |
| C10 | Empty input | Input validation | Passed |
| C11 | Modular visual identity | UW03 | Passed |
| C12 | Concept review | UW06 | Passed |
| C13 | Mesa Abierta improvements | UW09 | Passed |
| C14 | Functional animations | UW02 | Passed |
| C15 | Car engine repair | Abstention | Passed |
| C16 | Weather forecast | Abstention | Passed |

### Functional results

- Total cases: 16
- Satisfactory outcomes: 16
- Questions answered with sources: 10
- Correct abstentions: 5
- Empty input validations: 1
- Distinct source documents represented: 9

These results describe the selected functional
validation cases and do not establish general
question-answering accuracy.

## Observed document similarities

| Case | Source | Cosine similarity |
| --- | --- | --- |
| C01 | UW04 | 0.200033 |
| C02 | UW08 | 0.125356 |
| C03 | UW07 | 0.232856 |
| C04 | UW05 | 0.080935 |
| C05 | UW08 | 0.201243 |
| C06 | UW01 | 0.288850 |
| C11 | UW03 | 0.110921 |
| C12 | UW06 | 0.103486 |
| C13 | UW09 | 0.231216 |
| C14 | UW02 | 0.211246 |

Cosine similarity values are not confidence
probabilities or accuracy percentages.

## Execution examples

### Example 1 - Creative methods

Question:

How can we organize a session to generate design ideas?

Source: UW04 - Brief Idea Generation Session.

The answer retrieves the initial design problem,
project constraints, reference review, individual
sketching, discussion, and prototype direction
selection.

### Example 2 - Project lessons

Question:

What lessons were learned from the Aula Clara course catalog?

Source: UW07 - Project Closeout for the Aula Clara
Course Catalog.

The answer identifies the problems with the original
layout, the adjustments to course information, and
the lesson of reviewing content before choosing
a template.

### Example 3 - Visual proposal testing

Question:

How should the team test a visual proposal before development?

Source: UW05 - Short Test of a Visual Proposal.

The answer retrieves the preparation of a small
test, prototype construction, participant observation,
and the decision to continue, adjust, or discard
the proposal.

### Example 4 - Out-of-scope question

Question:

What is the price of Bitcoin?

Response:

I could not find enough relevant information in the
Umbral Web document collection to answer this question.

No supporting document is returned.

The complete original answers for all sixteen cases
are available in the functional evidence file.

## Running the chatbot

From the repository root, with the virtual
environment active:

```bash
python src/chatbot_cli.py
```

Available commands:

- /help: display available commands.
- /documents: list available documents.
- /exit: end the conversation.

Questions should be written in English.

## Programmatic usage

```python
from src.chatbot import DocumentChatbot

chatbot = DocumentChatbot()

response = chatbot.ask(
    "How can we organize a session to generate design ideas?"
)

print(response.answer)

for source in response.sources:
    print(source.document_id)
    print(source.title)
    print(source.similarity)
```

An existing RetrievalEngine instance can optionally
be passed to the DocumentChatbot constructor.

## Automated validation

Run the complete regression suite:

```bash
python -m unittest discover -s tests -v
```

| Test group | Passed | Total |
| --- | --- | --- |
| Retrieval | 9 | 9 |
| Recommendations | 20 | 20 |
| Chatbot | 20 | 20 |
| Total | 49 | 49 |

Two consecutive executions passed all 49 tests.

Observed execution times:

- Initial execution: 0.340 seconds.
- Evidence execution: 0.184 seconds.

The evidence execution returned exit code 0.

The chatbot tests verify:

- Shared retrieval infrastructure.
- Document collection coverage.
- Expected document sources.
- Out-of-scope question handling.
- Empty input handling.
- Relevant answer content.
- Original sentence integrity.
- Source and fragment consistency.
- Source metadata.
- Consecutive sentence selection.
- Sentence and document limits.
- Threshold validation.
- Response reproducibility.

No regressions were observed in the existing
retrieval and recommendation tests.

## Evidence files

- evidences/chatbot/functional_validation.txt
- evidences/chatbot/automated_tests.txt

The functional evidence includes the question,
answer, supporting sources, similarity score,
and extracted sentence count.

Both files were generated from actual executions
and encoded in UTF-8.

## Limitations

- The document collection contains nine texts.
- The chatbot depends on lexical similarity.
- Paraphrases and synonyms may not be recognized.
- Vocabulary coverage does not guarantee factual
  answerability.
- Short questions may be incorrectly rejected.
- Extractive answers may include secondary information
  or omit relevant details outside the selected window.
- Questions are processed independently.
- Persistent conversation memory is not implemented.
- Ranking weights and thresholds have not been
  independently calibrated.
- Functional validation is not a formal evaluation
  of general question-answering accuracy.
- The current interface operates through the command line.

## Potential improvements

1. Evaluate ranking weights and abstention thresholds
   using an independent annotated question collection.

2. Compare the current TF-IDF approach with contextual
   embeddings for improved paraphrase recognition.

3. Investigate more concise answer extraction while
   preserving relevant context and source traceability.

These improvements are proposals and have not been
implemented during F03.

## Integration readiness

The chatbot exposes a structured ChatbotResponse
object containing the question, answer, sources,
original fragments, and answered status.

This interface enables future integration with a
web application without duplicating chatbot logic.

Web interface integration and public deployment
remain pending.

## Conclusion

The second version of the document chatbot has
been implemented and functionally validated.

All sixteen selected functional cases produced
the expected behavior.

All twenty chatbot tests and twenty-nine previous
regression tests passed.

The chatbot is ready for web integration following
the final repository checks.