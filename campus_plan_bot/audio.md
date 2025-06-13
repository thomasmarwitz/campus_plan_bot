```
pixi run python -m campus_plan_bot.transcribe_audio transcribe --asr-type local --output local_asr_results_whisper_medium.csv --skip-conversion
```


```
pixi run python -i -m campus_plan_bot.transcribe_audio port \
    --input-csv phase1/data/evaluation/audio/local_asr_results.csv \
    --output-json phase1/data/evaluation/audio/local_asr_suite.json
```
