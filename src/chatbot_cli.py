"""Command-line interface for the Umbral Web chatbot."""

if __package__:
    from .chatbot import DocumentChatbot, ChatbotResponse
else:
    from chatbot import DocumentChatbot, ChatbotResponse


def print_response(response: ChatbotResponse) -> None:

    print()
    print("Umbral Web Assistant")
    print("=" * 65)

    print(response.answer)

    if not response.answered:
        print("-" * 65)
        return

    print("\nSources")
    print("-" * 65)

    for source in response.sources:

        print(
            f"{source.document_id} - "
            f"{source.title}"
        )

        print(
            f"Category: {source.category}"
        )

        print(
            f"Document similarity: "
            f"{source.similarity:.6f}"
        )

        print()

    print(
        f"Extracted sentences: "
        f"{len(response.fragments)}"
    )

    print("-" * 65)


def main() -> None:

    chatbot = DocumentChatbot()

    print("=" * 65)
    print("UMBRAL WEB - Document Chatbot")
    print("=" * 65)

    print(
        "\nAsk questions about the internal "
        "Umbral Web document collection."
    )

    print(
        "Questions should be written in English."
    )

    print("\nAvailable commands:")
    print("/help       Show available commands")
    print("/documents  List available documents")
    print("/exit       End the conversation")

    while True:

        try:

            question = input("\nYou: ").strip()

            if question.lower() == "/exit":

                print("\nChatbot session ended.")
                break

            if question.lower() == "/help":

                print("\nAvailable commands:")
                print("/help       Show available commands")
                print("/documents  List available documents")
                print("/exit       End the conversation")
                print(
                    "\nAsk a question about "
                    "the internal documents."
                )

                continue

            if question.lower() == "/documents":

                print("\nAvailable documents:")

                for document in chatbot.retrieval.documents:

                    print(
                        f"{document.doc_id} - "
                        f"{document.title}"
                    )

                continue

            response = chatbot.ask(question)

            print_response(response)

        except ValueError as error:

            print(f"\nError: {error}")

        except (KeyboardInterrupt, EOFError):

            print("\nChatbot session ended.")
            break


if __name__ == "__main__":
    main()