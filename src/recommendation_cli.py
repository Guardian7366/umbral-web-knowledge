"""Command-line demonstration of the recommendation system."""

if __package__:
    from .recommender import RecommendationEngine
else:
    from recommender import RecommendationEngine


def print_recommendations(recommendations) -> None:

    if not recommendations:
        print("\nNo relevant recommendations found.")
        return

    print("\nRecommended documents")
    print("=" * 65)

    for position, recommendation in enumerate(
        recommendations,
        start=1,
    ):

        document = recommendation.document

        print(f"\nRecommendation {position}")
        print(f"ID: {document.doc_id}")
        print(f"Title: {document.title}")
        print(f"Category: {document.category}")
        print(
            f"Cosine similarity: "
            f"{recommendation.similarity:.6f}"
        )

        terms = ", ".join(
            recommendation.shared_terms
        )

        print(
            f"Shared terms: {terms or 'N/A'}"
        )

        print(
            f"Explanation: "
            f"{recommendation.explanation}"
        )

        print("-" * 65)


def main() -> None:

    engine = RecommendationEngine()

    print("=" * 65)
    print("UMBRAL WEB - Document Recommendation System")
    print("=" * 65)

    while True:

        print("\nAvailable options:")
        print("1. Recommend by document")
        print("2. Recommend by search query")
        print("3. List available documents")
        print("0. Exit")

        try:

            option = input("\nSelect an option: ").strip()

            if option == "0":
                print("\nRecommendation session ended.")
                break

            elif option == "1":

                document_id = input(
                    "Enter document ID: "
                )

                recommendations = (
                    engine.recommend_by_document(
                        document_id
                    )
                )

                print_recommendations(
                    recommendations
                )

            elif option == "2":

                query = input(
                    "Enter your search query: "
                )

                recommendations = (
                    engine.recommend_by_query(query)
                )

                print_recommendations(
                    recommendations
                )

            elif option == "3":

                print("\nAvailable documents:")

                for document in engine.retrieval.documents:

                    print(
                        f"{document.doc_id} - "
                        f"{document.title}"
                    )

            else:
                print("\nInvalid option.")

        except ValueError as error:
            print(f"\nError: {error}")

        except (KeyboardInterrupt, EOFError):
            print("\nRecommendation session ended.")
            break


if __name__ == "__main__":
    main()