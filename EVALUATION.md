# Evaluating the Campus Plan Bot

This document outlines the procedure for evaluating the campus plan bot using the evaluation script `eval/evaluation.py`.

## Prerequisites

- Ensure all Python dependencies are installed.
- The evaluation datasets are expected to be located in the `data/evaluation/` directory.
- Set an environment variable `CHUTES_KEY=cpk_...`

## Running the Evaluation

The evaluation script uses `click` for its command-line interface. You can view all available commands and options by running:

```bash
python eval/evaluation.py --help
```

### Output Directory

The evaluation results will be saved to a directory you specify. For these instructions, we'll use `data/evaluation/results/EVAL_NAME` as the output path. Replace `EVAL_NAME` with a descriptive name for your evaluation run.

Before running, create the directory:

```bash
export EVAL_NAME="my-evaluation"
mkdir -p data/evaluation/results/$EVAL_NAME
```

### 1. Single-Turn Synthetic Datasets

To evaluate the single-turn synthetic datasets for each intent (e.g., `building_location`, `opening_hours`), run the `evaluate_single_synthetic` command. This command automatically finds all `*synthetic.json` files in the `data/evaluation/single_turn/` directory.

```bash
python eval/evaluation.py evaluate-single-synthetic \
    --output-dir data/evaluation/results/$EVAL_NAME
```

This will generate CSV files for each synthetic test, including:

- `building_location_synthetic.csv`
- `closed_until_synthetic.csv`
- `navigation_link_synthetic.csv`
- `open_now_synthetic.csv`
- `open_until_synthetic.csv`
- `open_website_synthetic.csv`
- `opening_hours_synthetic.csv`
- `wheelchair_accessible_synthetic.csv`

### 2. Multi-Turn Conversations

To evaluate the multi-turn conversation dataset, use the `evaluate-file` command. The default test path is already set to the multi-turn dataset.

```bash
python eval/evaluation.py evaluate-file \
    --output-dir data/evaluation/results/$EVAL_NAME
```

This will generate `multi_turns.csv` in your output directory.

### 3. ASR Datasets

You can also use the `evaluate-file` command to evaluate datasets with simulated Automatic Speech Recognition (ASR) errors. You must provide the path to the specific ASR test file.

Assuming the ASR test files are located at `data/evaluation/local_asr_suite/`:

```bash
# Evaluate whisper_base ASR data
python eval/evaluation.py evaluate_file \
    --test-path data/evaluation/local_asr_suite/local_asr_suite_whisper_base.json \
    --output-dir data/evaluation/results/$EVAL_NAME

# Evaluate whisper_small ASR data
python eval/evaluation.py evaluate_file \
    --test-path data/evaluation/local_asr_suite/local_asr_suite_whisper_small.json \
    --output-dir data/evaluation/results/$EVAL_NAME
```

These commands will produce the following result files:

- `local_asr_suite_whisper_base.csv`
- `local_asr_suite_whisper_small.csv`
