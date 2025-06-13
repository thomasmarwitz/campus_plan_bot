#!/usr/bin/env python3

import glob
import os
import subprocess
import time
from pathlib import Path

import click
import pandas as pd
from loguru import logger

from campus_plan_bot.local_asr import LocalASR
from campus_plan_bot.remote_asr import RemoteASR


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
    asr = LocalASR(None) if asr_type == "local" else RemoteASR(None)

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


@click.command()
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
def main(asr_type: str, output_path: str, skip_conversion: bool):
    """Transcribes all single-turn and multi-turn audio files using the
    specified ASR, and saves the results to a CSV file."""
    logger.remove()
    logger.add(lambda msg: click.echo(msg, err=True), level="INFO")
    logger.add("file_{time}.log", level="DEBUG")  # For detailed logs

    run_transcription(asr_type, output_path, skip_conversion)


if __name__ == "__main__":
    main()
