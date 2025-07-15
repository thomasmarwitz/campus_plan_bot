import sys
from pathlib import Path

import pandas as pd
from loguru import logger

# Add project root to path to allow imports
sys.path.append(str(Path(__file__).resolve().parents[1]))

from campus_plan_bot.interfaces.persistence_types import Conversation, Message, Role
from campus_plan_bot.query_rewriter import QuestionRephraser
from campus_plan_bot.rag import RAG

# Constants for file paths
EVAL_DATA_PATH = Path("data/campusplan_evaluation.csv")
RAG_EVAL_DATASET_PATH = Path("data/rag_evaluation_dataset.csv")


def evaluate_rag():
    """Evaluates the RAG component using a predefined dataset, including query
    rephrasing."""
    logger.info("Starting RAG evaluation with query rephrasing...")

    # 1. Initialize components
    logger.info(f"Initializing RAG with data from: {EVAL_DATA_PATH}")
    rag = RAG.from_file(EVAL_DATA_PATH, id_column_name="identifikator")
    rephraser = QuestionRephraser()

    # 2. Load the evaluation dataset
    logger.info(f"Loading evaluation dataset from: {RAG_EVAL_DATASET_PATH}")
    eval_df = pd.read_csv(RAG_EVAL_DATASET_PATH)

    successful_retrievals = 0
    failed_queries = []

    # 3. Run evaluation
    for index, row in eval_df.iterrows():
        query = row["query"]
        expected_id = row["expected_identifikator"]
        logger.info(f"Original query: '{query}'")

        # Rephrase query
        conversation = Conversation.new()
        conversation.add_message(Message.from_content(query, Role.USER))
        rephrased_query = rephraser.rephrase(conversation)
        logger.info(f"Rephrased query: '{rephrased_query}'")

        retrieved_docs = rag.retrieve_context(rephrased_query, limit=5)
        retrieved_ids = [doc.id for doc in retrieved_docs]

        if expected_id in retrieved_ids:
            successful_retrievals += 1
            logger.success(f"  -> SUCCESS: Found '{expected_id}' in results.")
        else:
            failed_queries.append(
                {
                    "query": query,
                    "rephrased_query": rephrased_query,
                    "expected": expected_id,
                    "retrieved": retrieved_ids,
                }
            )
            logger.error(f"  -> FAILURE: Did not find '{expected_id}' in results.")

    # 4. Report results
    total_queries = len(eval_df)
    accuracy = (successful_retrievals / total_queries) * 100 if total_queries > 0 else 0

    print("\n--- RAG Evaluation Report (with Query Rephrasing) ---")
    print(f"Total Queries: {total_queries}")
    print(f"Successful Retrievals: {successful_retrievals}")
    print(f"Accuracy (Recall@5): {accuracy:.2f}%")

    if failed_queries:
        print("\n--- Failed Queries ---")
        for failure in failed_queries:
            print(f"  Query: \"{failure['query']}\"")
            print(f"  Rephrased: \"{failure['rephrased_query']}\"")
            print(f"    Expected: {failure['expected']}")
            print(f"    Retrieved: {failure['retrieved']}\n")
    print("-------------------------\n")
    logger.info("RAG evaluation finished.")


if __name__ == "__main__":
    evaluate_rag()
