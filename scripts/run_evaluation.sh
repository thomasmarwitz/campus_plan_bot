#!/bin/bash

# Script configuration
SLEEP=15
MAX_RETRIES=3
CHUNK_SIZE=10

# Check for output directory argument
if [ -z "$1" ]; then
  echo "Usage: $0 <output_directory>"
  exit 1
fi

OUTPUT_DIR=$1
mkdir -p "$OUTPUT_DIR"

# Function to execute a command with retry logic
execute_with_retry() {
  local cmd="$1"
  local retries=0
  until $cmd; do
    retries=$((retries+1))
    if [ $retries -ge $MAX_RETRIES ]; then
      echo "Command failed after $MAX_RETRIES attempts: $cmd"
      return 1
    fi
    echo "Command failed. Retrying in $SLEEP seconds..."
    sleep $SLEEP
  done
  return 0
}

# --- Evaluation Commands ---

echo "Running single-turn synthetic evaluation..."
CMD_SINGLE_TURN="pixi run python eval/evaluation.py evaluate-single-synthetic --output-dir $OUTPUT_DIR --chunk-size $CHUNK_SIZE"
execute_with_retry "$CMD_SINGLE_TURN"

echo "Running multi-turn evaluation..."
CMD_MULTI_TURN="pixi run python eval/evaluation.py evaluate-file --output-dir $OUTPUT_DIR --chunk-size $CHUNK_SIZE"
execute_with_retry "$CMD_MULTI_TURN"

echo "Running ASR evaluation (whisper_base)..."
CMD_ASR="pixi run python eval/evaluation.py evaluate-file --test-path data/evaluation/audio/local_asr_suite_whisper_base.json --output-dir $OUTPUT_DIR --chunk-size $CHUNK_SIZE"
execute_with_retry "$CMD_ASR"

echo "All evaluations completed."
