from sklearn.metrics.pairwise import cosine_similarity
from os.path import basename
import numpy as np
import re

from classifier import (
    load_documents,
    build_vectorizer,
)

def main() -> None:
    # Load documents and build the vectorizer for similarity search
    documents = load_documents()
    vectorizer = build_vectorizer()
    X =  vectorizer.fit_transform([d.text for d in documents]) 

    while True:
        print("=" * 50)
        query = input("Enter your query: ")
        print("=" * 50)
        print()
        if not query:
            break
        # Transform the query into the same vector space as the documents
        query_vec = vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, X)

        # Display Top 3 most similar documents where similarity is greater than zero
        top_indices = [i for i in np.argsort(similarities[0])[::-1][:3] if similarities[0][i] > 0]
        for idx in top_indices:
            print(f"Similarity: {similarities[0][idx]} - Document: {basename(documents[idx].path)}")

            # Display the content of the document with query colored
            doc_text = documents[idx].text
            for word in query.split():
                doc_text = re.sub(rf'\b{re.escape(word)}\b', f"\033[91m{word}\033[0m", doc_text)
            print(doc_text)
            print()
        print()

if __name__ == "__main__":
    main()
