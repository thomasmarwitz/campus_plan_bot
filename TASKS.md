# Current Tasks

* [X] Compose a unified testing bash script with corresponding pixi task to run it.

  * [X] Create pixi task
  * [X] Create script (`scripts/run_evaluation.sh`)
    * [X] Add `SLEEP` and `MAX_RETRIES` variables at the top of the script.
    * [X] Add a `CHUNK_SIZE` variable, defaulting to 10.
    * [X] Implement a function to execute a command with the specified retry logic.
    * [X] The script must accept one mandatory argument: the output directory path for the results.
    * [X] The script should run the following evaluation commands using the retry logic:
      * `evaluate-single-synthetic`
      * `evaluate-file` for the multi-turn dataset.
      * `evaluate-file` for the `whisper_base` ASR dataset (`data/evaluation/audio/local_asr_suite_whisper_base.json`).
  * [X] Update `eval/create_plots.py`:
    * [X] Modify the `compare` command to accept a single directory path for the `--input-dir` argument.
    * [X] If a single directory is provided, glob for all subdirectories within it.
    * [X] Automatically generate labels for the comparison plots from the subdirectory names.
