from pathlib import Path

import click
import pandas as pd
from rich import print

from campus_plan_bot.rag import RAG


@click.command()
@click.argument("phrase")
def debug_rag(phrase: str):
    """Debugs the RAG system by retrieving documents for a given phrase and
    printing them to the console."""
    data_file_path = Path("data/campusplan_evaluation.csv")
    if not data_file_path.exists():
        print(f"Data file '{data_file_path}' not found. Exiting.")
        return

    df = pd.read_csv(data_file_path, dtype={"old_identifikator": str})
    rag = RAG.from_df(df, id_column_name="old_identifikator")

    print(f"Retrieving documents for phrase: '{phrase}'")
    retrieved_docs = rag.retrieve_context(phrase, limit=5)

    if not retrieved_docs:
        print("No documents found for this phrase.")
        return

    print("\n[bold green]Retrieved Documents:[/bold green]")
    for i, doc in enumerate(retrieved_docs, 1):
        print(
            f"\n--- Document {i} (ID: {doc.id}, Score: {doc.relevance_score:.4f}) ---"
        )


if __name__ == "__main__":
    debug_rag()
