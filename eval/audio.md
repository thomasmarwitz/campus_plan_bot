```
pixi run python -m eval.transcribe_audio transcribe --asr-type local --output local_asr_results_whisper_medium.csv --skip-conversion
```


```
pixi run python -i -m eval.transcribe_audio port \
    --input-csv data/evaluation/audio/local_asr_results.csv \
    --output-json data/evaluation/audio/local_asr_suite.json
```
