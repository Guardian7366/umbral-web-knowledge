"""Command-line interface for document retrieval."""

import re

if __package__:
    from .retrieval import RetrievalEngine
else:
    from retrieval import RetrievalEngine


def main() -> None:
    engine = RetrievalEngine()

    while True:
        print("=" * 50)

        try:
            query = input("Enter your query: ")
        except (KeyboardInterrupt, EOFError):
            print("\nSearch session ended.")
            break

        print("=" * 50)
        print()

        if not query.strip():
            break

        results = engine.search(query)

        if not results:
            print("No relevant documents found.")
            print()
            continue

        for result in results:
            print(
                f"Similarity: {result.similarity} - "
                f"Document: {result.document.path.name}"
            )

            doc_text = result.document.text

            for word in query.split():
                doc_text = re.sub(
                    rf"\b{re.escape(word)}\b",
                    f"\033[91m{word}\033[0m",
                    doc_text,
                )

            print(doc_text)
            print()

        print()


if __name__ == "__main__":
    main()