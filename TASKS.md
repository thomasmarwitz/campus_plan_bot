# Current Tasks

## Unified testing script

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

## Updated system prompt

* [ ] Extract general system prompt (campus_plan_bot/constants.py) to markdown and store in existing prompts dir (campus_plan_bot/prompts)
* [ ] Prompt should be in German!
* [ ] Structure using markdown headings

  * [ ] Add a capabilities section. Include all capabilites: answering about location (address), general opening times questions, how can I get to abuilding (directions), check for websites availability, indicate whether a building is wheelchair accesible and potentially give further details on that.
  * [ ] Add a section if encountering an unknown request, the request should then be fulfilled to the best of the LLMs knowledge, considering all context.
  * [ ] Add section on navigation link generation (what format [google]) and when to give the user one (user asks not for an address but HOW to get there, or they ask for directions or they explicitely ask for navigation link)
  * [ ] Add section for opening hours related questions (there are 1+3 types of questions)
    first is about general opening hours, here the relevant retrieved data can just be repeated
    other three are: is it open right now, when does a building open, when does it close. The system should use the current time (in system prompt) to "calculate" / give a rounded answer when does it open, e.g. in around 9 hours.
  * [ ] Add section (contextual information) that adds the current system time (use placeholder that is formatted later on)
  * [ ] Inlcude an examples section (can be empty for now, we'll fill that later)
* [ ] Build a link extractor component that is invoked after a response of the chatbot is generated. This component should prog. check whether a google maps link is contained. If so, the component returns a named tuple with an answer (that is popoulated using a constant value "Ich habe die Website für dich geöffnet") and the link itself. if there is no link contained, nothing happens. the answer stays as it is

  *  Use the if name is main syntax to add some manual test cases for the component in the same file. you can iterate by executing the component until you see that it works.
