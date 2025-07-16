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
```

### 1. Single-Turn Synthetic Datasets

To evaluate the single-turn synthetic datasets for each intent (e.g., `building_location`, `opening_hours`), run the `evaluate_single_synthetic` command. This command automatically finds all `*synthetic.json` files in the `data/evaluation/single_turn/` directory.

```bash
pixi run python eval/evaluation.py evaluate-single-synthetic \
    --output-dir data/evaluation/results/$EVAL_NAME \
    --chunk-size 10
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
pixi run python eval/evaluation.py evaluate-file \
    --output-dir data/evaluation/results/$EVAL_NAME \
    --chunk-size 10
```

This will generate `multi_turns.csv` in your output directory.

### 3. ASR Datasets

You can also use the `evaluate-file` command to evaluate datasets with simulated Automatic Speech Recognition (ASR) errors. You must provide the path to the specific ASR test file.

Assuming the ASR test files are located at `data/evaluation/local_asr_suite/`:

```bash
# Evaluate whisper_base ASR data
pixi run python eval/evaluation.py evaluate-file \
    --test-path data/evaluation/audio/local_asr_suite_whisper_base.json \
    --output-dir data/evaluation/results/$EVAL_NAME \
    --chunk-size 10

# Evaluate whisper_small ASR data
pixi run python eval/evaluation.py evaluate-file \
    --test-path data/evaluation/local_asr_suite/local_asr_suite_whisper_small.json \
    --output-dir data/evaluation/results/$EVAL_NAME
```

These commands will produce the following result files:

- `local_asr_suite_whisper_base.csv`
- `local_asr_suite_whisper_small.csv`

## Generating Plots from Evaluation Results

The `eval/create_plots.py` script can be used to generate visualizations from the evaluation results. It offers two main commands: `single` for analyzing one evaluation run and `compare` for comparing multiple runs.

### Generating Plots for a Single Run

To generate a full suite of plots and reports for a single evaluation run, use the `single` command:

```bash
# Replace with your actual results and output directories
python eval/create_plots.py single \
    data/evaluation/results/$EVAL_NAME \
    docs/phase2/plots/$EVAL_NAME
```

### Comparing Multiple Evaluation Runs

The `compare` command is designed to generate comparison plots and a summary CSV for multiple evaluation runs. This is useful for tracking performance changes between different model versions or configurations.

You must provide the paths to each results directory using the `-i` or `--input-dir` flag and a corresponding label for each using the `-n` or `--name` flag.

#### Example

To compare the results from a `phase2` baseline against a `component-chosen-fields` run, you can execute the following command:pixi run python eval/create_plots.py compare -i data/evaluation/results/phase2 -i data/evaluation/results/component-chosen-fields -i data/evaluation/results/better-rag -n baseline -n "#1-chosen-fields" -n "#2-better-rag" --output-dir docs/phase3/report/comparison --phrases-file eval/phrases.txtpixi run python eval/create_plots.py compare \

```bash
pixi run python eval/create_plots.py compare -i data/evaluation/results/phase2 -i
data/evaluation/results/component-chosen-fields -i data/evaluation/results/better-rag -i data/evaluation/results/link_gen -n baseline -n "#1-chosen-fields" -n "#2-better-rag" -n  "#4-system-prompt" --output-dir docs/phase3/report/comparison --phrases-file eval/phrases.txt -o docs/phase3/report/comparison-#4
```

This command will create a new directory (by default `docs/phase2/plots_comparison`) containing:

- **`overall_performance_comparison.png`**: Compares LLM Judge scores across major evaluation categories.
- **`single_turn_performance_comparison.png`**: Compares LLM Judge scores for each single-turn category.
- **`evaluation_summary_comparison.csv`**: Provides a summary of test cases and pass/fail counts for each run, making it easy to see deltas in performance.
