import asyncio
import json
from pathlib import Path
import time

import pandas as pd
from rich import print
from tqdm import tqdm

from campus_plan_bot.asr_processing import AsrProcessor
from campus_plan_bot.clients.chute_client import ChuteModel
from campus_plan_bot.rag import RAG


async def evaluate_asr_fixing():
    """Evaluates the ASR fixing component on the first turn of multi-turn
    conversations."""
    asr_suite_path = Path("data/evaluation/audio/local_asr_suite_whisper_base.json")
    with open(asr_suite_path) as f:
        evaluation_data = json.load(f)

    data_file_path = Path("data/campusplan_evaluation.csv")
    if not data_file_path.exists():
        print(f"Data file '{data_file_path}' not found. Skipping evaluation.")
        return

    df = pd.read_csv(data_file_path, dtype={"old_identifikator": str})

    rag = RAG.from_df(df, id_column_name="old_identifikator")
    asr_processor = AsrProcessor()
    # ChuteModel(model="Qwen/Qwen3-32B", no_think=True, strip_think=True)

    results = []
    for interaction in tqdm(
        evaluation_data,
        desc="Evaluating ASR Fixing",
    ):
        # We only evaluate the very first prompt in a conversation
        first_turn = interaction["prompts"][0]
        original_query = first_turn["asr_prompt"]
        expected_id = str(first_turn["input_data"])

        # Step 1: fix ASR errors
        start_time = time.time()
        fixed_query = await asr_processor.fix_asr(original_query)
        end_time = time.time()
        #fixed_query = ""

        # Step 2: retrieve relevant documents
        retrieved_docs = rag.retrieve_context(original_query, limit=5, asr_fixed_query=fixed_query)
        retrieved_ids = [str(doc.id) for doc in retrieved_docs]

        # Step 3: check if the expected document was retrieved
        passed = expected_id in retrieved_ids

        results.append(
            {
                "original_query": original_query,
                "fixed_query": fixed_query,
                "retrieved_docs": ",".join(retrieved_ids),
                "expected_id": expected_id,
                "passed": passed,
                "time_taken": end_time - start_time,
            }
        )

    results_df = pd.DataFrame(results)

    output_dir = Path("data/evaluation/results/asr-fixing")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "asr_fixing_evaluation.csv"
    results_df.to_csv(output_path, index=False)
    print(f"Evaluation results saved to {output_path}")

    # Calculate and print metrics
    total_prompts = len(results_df)
    successful_retrievals = results_df["passed"].sum()
    success_ratio = (
        successful_retrievals / total_prompts if total_prompts > 0 else 0
    )

    print(
        f"Overall success ratio: {success_ratio:.2f} ({successful_retrievals}/{total_prompts})"
    )


if __name__ == "__main__":
    asyncio.run(evaluate_asr_fixing())
