#!/usr/bin/env python3

import glob
import json
import os
import subprocess
import time
from pathlib import Path

import click
import pandas as pd
from loguru import logger

from campus_plan_bot.evaluation import TestCase
from campus_plan_bot.input.local_asr import LocalASR
from campus_plan_bot.input.remote_asr import RemoteASR


def convert_to_wav(input_file: str, output_file: str):
    """Convert audio file to WAV format using ffmpeg."""
    try:
        # Convert to WAV using ffmpeg
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                input_file,
                "-acodec",
                "pcm_s16le",  # 16-bit PCM
                "-ar",
                "16000",  # 16kHz sampling rate
                "-ac",
                "1",  # mono
                "-y",  # overwrite output file
                output_file,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting file: {input_file}")
        logger.error(f"ffmpeg stdout: {e.stdout}")
        logger.error(f"ffmpeg stderr: {e.stderr}")
        raise


@click.group()
def cli():
    """A CLI tool for transcribing audio files and porting them to test
    cases."""
    pass


@cli.command()
@click.option(
    "--asr-type",
    type=click.Choice(["local", "remote"]),
    required=True,
    help="Specify which ASR to use.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, writable=True),
    required=True,
    help="Path to save the output CSV file.",
)
@click.option(
    "--skip-conversion",
    is_flag=True,
    help="Skip M4A to WAV conversion and use existing WAV files.",
)
def transcribe(asr_type: str, output_path: str, skip_conversion: bool):
    """Transcribes all single-turn and multi-turn audio files using the
    specified ASR, and saves the results to a CSV file."""
    logger.remove()
    logger.add(lambda msg: click.echo(msg, err=True), level="INFO")
    logger.add("file_{time}.log", level="DEBUG")  # For detailed logs
    run_transcription(asr_type, output_path, skip_conversion)


@cli.command()
@click.option(
    "--input-csv",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Path to the input transcription CSV file.",
)
@click.option(
    "--output-json",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    required=True,
    help="Path for the output JSON test case file.",
)
@click.option(
    "--single-turn-data-dir",
    type=str,
    default="phase1/data/evaluation/single_turn/",
    help="Directory containing single-turn ground-truth JSON files.",
)
@click.option(
    "--multi-turn-data-file",
    type=str,
    default="phase1/data/evaluation/multi_turn/multi_turns.json",
    help="Path to the multi-turn ground-truth JSON file.",
)
def port(
    input_csv: Path,
    output_json: Path,
    single_turn_data_dir: str,
    multi_turn_data_file: str,
):
    """Ports a transcription CSV to a JSON test case file."""
    logger.info(f"Porting data from {input_csv} to {output_json}...")
    df = pd.read_csv(input_csv)
    ported_test_cases = []

    # --- Process Multi-turn cases ---
    multi_turn_df = df[df["type"] == "multi"].copy()
    if not multi_turn_df.empty:
        logger.info("Processing multi-turn cases...")
        with open(multi_turn_data_file) as f:
            multi_turn_ground_truth = [
                TestCase.model_validate(tc) for tc in json.load(f)
            ]

        multi_turn_df["case_idx"] = multi_turn_df["file_stem"].apply(
            lambda x: int(x.split("-")[0])
        )
        multi_turn_df["turn_idx"] = multi_turn_df["file_stem"].apply(
            lambda x: int(x.split("-")[1])
        )

        for case_idx, group in multi_turn_df.groupby("case_idx"):
            if case_idx >= len(multi_turn_ground_truth):
                raise IndexError(
                    f"Case index {case_idx} is out of bounds for multi-turn ground truth."
                )

            test_case: TestCase = multi_turn_ground_truth[case_idx]
            for _, row in group.iterrows():
                turn_idx: int = int(row["turn_idx"])
                if turn_idx >= len(test_case.prompts):
                    raise IndexError(
                        f"Turn index {turn_idx} is out of bounds for case {case_idx}."
                    )

                test_case.prompts[turn_idx].asr_prompt = row["transcription"]
            ported_test_cases.append(test_case)

    # --- Process Single-turn cases ---
    single_turn_df = df[df["type"] == "single"].copy()
    if not single_turn_df.empty:
        logger.info("Processing single-turn cases...")
        for _, row in single_turn_df.iterrows():
            file_stem = row["file_stem"]
            try:
                base_name, index_str = file_stem.rsplit("-", 1)
                case_idx = int(index_str)
            except ValueError:
                raise ValueError(
                    f"Could not parse file_stem for single-turn case: {file_stem}"
                )

            ground_truth_file = Path(single_turn_data_dir) / f"{base_name}.json"
            if not ground_truth_file.exists():
                raise FileNotFoundError(
                    f"Ground truth file not found for stem {base_name}: {ground_truth_file}"
                )

            with open(ground_truth_file) as f:
                single_turn_ground_truth = [
                    TestCase.model_validate(tc) for tc in json.load(f)
                ]

            if not 0 <= case_idx < len(single_turn_ground_truth):
                raise IndexError(
                    f"Case index {case_idx} is out of bounds for ground truth file {ground_truth_file}."
                )

            test_case = single_turn_ground_truth[case_idx]
            test_case.prompts[0].asr_prompt = row["transcription"]
            ported_test_cases.append(test_case)

    # --- Save to JSON ---
    with open(output_json, "w") as f:
        json.dump([tc.model_dump() for tc in ported_test_cases], f, indent=2)
    logger.info(
        f"Successfully ported {len(ported_test_cases)} test cases to {output_json}."
    )


def run_transcription(asr_type: str, output_path: str, skip_conversion: bool):
    """Transcribe audio files using the specified ASR and save results."""

    # --- 1. File Discovery ---
    single_turn_path = "phase1/data/evaluation/audio/single_turn/"
    multi_turn_path = "phase1/data/evaluation/audio/multi_turn/"

    single_files_m4a = sorted(glob.glob(os.path.join(single_turn_path, "*.m4a")))
    single_files_m4a = [f for f in single_files_m4a if not Path(f).stem.endswith("_2")]
    multi_files_m4a = sorted(glob.glob(os.path.join(multi_turn_path, "*.m4a")))
    all_m4a_files = single_files_m4a + multi_files_m4a

    # --- 2. Conversion (optional) ---
    if not skip_conversion:
        with click.progressbar(all_m4a_files, label="Converting to WAV") as files:
            for file in files:
                wav_path = file.replace(".m4a", ".wav")
                if not os.path.exists(wav_path):
                    convert_to_wav(file, wav_path)

    single_files_wav = sorted(glob.glob(os.path.join(single_turn_path, "*.wav")))
    single_files_wav = [f for f in single_files_wav if not Path(f).stem.endswith("_2")]
    multi_files_wav = sorted(glob.glob(os.path.join(multi_turn_path, "*.wav")))
    all_wav_files = single_files_wav + multi_files_wav

    # --- 3. Load existing results or initialize DataFrame ---
    if os.path.exists(output_path):
        logger.info(f"Output file found at {output_path}. Resuming...")
        df = pd.read_csv(output_path)
        existing_files = set(df["file_stem"])
        files_to_process = [
            f
            for f in all_wav_files
            if Path(f).stem not in existing_files
            or df[df["file_stem"] == Path(f).stem]["error"].notna().any()
        ]
        results = df.to_dict("records")
    else:
        logger.info("No output file found. Starting fresh.")
        files_to_process = all_wav_files
        results = []

    if not files_to_process:
        logger.info("All files have been processed. Exiting.")
        return

    # --- 4. ASR Initialization ---
    asr = (
        LocalASR(None, whisper_model_name="openai/whisper-medium")
        if asr_type == "local"
        else RemoteASR(None)
    )

    # --- 5. Transcription Loop ---
    total_files = len(files_to_process)
    logger.info(f"Processing {total_files} files...")

    for i, wav_file in enumerate(files_to_process, 1):
        file_stem = Path(wav_file).stem
        file_type = "single" if "single_turn" in wav_file else "multi"
        logger.info(f"Processing file {i}/{total_files}: {os.path.basename(wav_file)}")

        start_time = time.time()
        transcript = ""
        error_message = None

        try:
            transcript = asr.transcribe(wav_file)
        except Exception as e:
            error_message = str(e)
            logger.error(f"Initial transcription failed for {wav_file}: {e}")
            if asr_type == "remote":
                logger.info(f"Retrying remote ASR for {wav_file}...")
                try:
                    transcript = asr.transcribe(wav_file)
                    error_message = None  # Succeeded on retry
                except Exception as e2:
                    error_message = str(e2)
                    logger.error(f"Retry failed for {wav_file}: {e2}")

        processing_time = time.time() - start_time

        # Update existing record or add new one
        record_found = False
        for record in results:
            if record["file_stem"] == file_stem:
                record["transcription"] = transcript
                record["error"] = error_message
                record["processing_time"] = processing_time
                record_found = True
                break

        if not record_found:
            results.append(
                {
                    "file_stem": file_stem,
                    "transcription": transcript,
                    "type": file_type,
                    "error": error_message,
                    "processing_time": processing_time,
                }
            )

        # Save after each file
        pd.DataFrame(results).to_csv(output_path, index=False)

    logger.info("All files processed.")


if __name__ == "__main__":
    cli()
