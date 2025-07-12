import json
from pathlib import Path

import pandas as pd
from rich import print
from tqdm import tqdm

from campus_plan_bot.interfaces.persistence_types import Conversation, Message, Role
from campus_plan_bot.query_rewriter import QuestionRephraser

# sys.path.append(str(Path(__file__).resolve().parents[1]))
from campus_plan_bot.rag import RAG


def evaluate_rag_multi_turn():
    """Evaluates the RAG system on multi-turn conversations using query
    rephrasing."""
    multi_turn_eval_path = Path("data/evaluation/multi_turn/multi_turns.json")
    with open(multi_turn_eval_path) as f:
        evaluation_data = json.load(f)

    data_file_path = Path("data/campusplan_evaluation.csv")
    if not data_file_path.exists():
        print(f"Data file '{data_file_path}' not found. Skipping evaluation.")
        return

    df = pd.read_csv(data_file_path, dtype={"old_identifikator": str})

    rag = RAG.from_df(df, id_column_name="old_identifikator")
    rephraser = QuestionRephraser()

    results = []
    for interaction in tqdm(
        evaluation_data,
        desc="Evaluating RAG with rephrasing on multi-turn conversations",
    ):
        conversation = Conversation.new()
        for i, turn in enumerate(interaction["prompts"]):
            prompt = turn["prompt"]  # Using original prompt for rephrasing
            expected_id = str(turn["input_data"])

            conversation.add_message(Message.from_content(prompt, Role.USER))
            rephrased_query = rephraser.rephrase(conversation)

            retrieved_docs = rag.retrieve_context(rephrased_query, limit=5)

            position = -1
            for doc_idx, doc in enumerate(retrieved_docs):
                if str(doc.id) == expected_id:
                    position = doc_idx + 1
                    break

            failed = 1 if position == -1 else 0

            # Add a mock assistant response for the next turn's context
            if not failed:
                try:
                    retrieved_row = df[df["old_identifikator"].str.contains(expected_id)].iloc[0]
                    building_name = retrieved_row.get("name", expected_id)
                    assistant_response = (
                        f"Informationen zu {building_name} ({expected_id}) gefunden."
                    )
                except IndexError:
                    assistant_response = "Informationen gefunden."
                conversation.add_message(
                    Message.from_content(assistant_response, Role.ASSISTANT)
                )
            else:
                assistant_response = (
                    "Ich konnte dazu leider keine Informationen finden."
                )
                conversation.add_message(
                    Message.from_content(assistant_response, Role.ASSISTANT)
                )

            results.append(
                {
                    "id": expected_id,
                    "query": prompt,
                    "rephrased_query": rephrased_query,
                    "position": position,
                    "num_turn": i + 1,
                    "failed": failed,
                }
            )

    results_df = pd.DataFrame(results)

    output_dir = Path("data/evaluation/results/multi_turn")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "rag_evaluation_with_rephrasing.csv"
    results_df.to_csv(output_path, index=False)
    print(f"Evaluation results saved to {output_path}")

    # compute: save all failed retrievals where num_turn = 1
    failed_retrievals_num_turn_1 = results_df[
        (results_df["num_turn"] == 1) & (results_df["failed"] == 1)
    ]
    failed_retrievals_num_turn_1.to_csv(
        output_dir / "failed_retrievals_num_turn_1_with_rephrasing.csv", index=False
    )

    # Calculate metrics
    total_prompts = len(results_df)
    successful_retrievals = total_prompts - results_df["failed"].sum()
    overall_success_ratio = (
        successful_retrievals / total_prompts if total_prompts > 0 else 0
    )

    print(
        f"Overall success ratio: {overall_success_ratio:.2f} ({successful_retrievals}/{total_prompts})"
    )

    # Per-turn success ratio
    turns = sorted(results_df["num_turn"].unique())
    for turn_id in turns:
        turn_results_df = results_df[results_df["num_turn"] == turn_id]
        turn_total = len(turn_results_df)
        turn_successful = turn_total - turn_results_df["failed"].sum()
        turn_success_ratio = turn_successful / turn_total if turn_total > 0 else 0
        print(
            f"  Turn {turn_id} success ratio: {turn_success_ratio:.2f} ({turn_successful}/{turn_total})"
        )


if __name__ == "__main__":
    evaluate_rag_multi_turn()
