from pathlib import Path

import pytest

from campus_plan_bot.rag import RAG

# This path is relative to the project root, where pytest is usually run.
DATA_FILE_PATH = Path("data/campusplan_enriched.csv")


@pytest.mark.skipif(not DATA_FILE_PATH.exists(), reason="Data file 'campusplan_enriched.csv' not found")
def test_rag_retrieval():
    """
    A simple test to check if the RAG component can be executed and works.
    This test performs a simple retrieval and prints the results.
    """
    print("Initializing RAG component from:", DATA_FILE_PATH)
    rag = RAG.from_file(DATA_FILE_PATH)

    query = "Where is building 50.20?"
    print(f"\nRetrieving context for query: '{query}'")

    documents = rag.retrieve_context(query, limit=3)

    print("\n--- Retrieval Results ---")
    if documents:
        for doc in documents:
            print(f"  ID: {doc.id}, Score: {doc.relevance_score}, Name: {doc.data.get('name')}")
    else:
        print("  No documents found.")
    print("-------------------------\n")
    print("Test execution finished.")


if __name__ == "__main__":
    # This allows running the test script directly.
    if not DATA_FILE_PATH.exists():
        print(f"Skipping test: Data file not found at {DATA_FILE_PATH}")
    else:
        test_rag_retrieval() 