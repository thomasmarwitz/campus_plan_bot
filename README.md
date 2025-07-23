# Dialogue practical

## Installation

This installs `campus_plan_bot` as an editable Python project to enable imports from arbitrary locations inside the `campus_plan_bot` folder.

```bash
pixi run postinstall
```

## Serving Frontend / Backend

```bash
pixi run uvicorn backend.app:app --reload
```

The website can then be reached under [http://127.0.0.1:8000/?lat=49.01025&amp;lon=8.41890](http://127.0.0.1:8000/?lat=49.01025&lon=8.41890)

## System Architecture


More details on the system architecture can be found [here](PLANNING.md).

## Testing

More details on testing can be found [here](TESTING.md).

## Evaluation

More details on evaluating the model can be found [here](EVALUATION.md).


## Disable Tokenizers Parallelism

```
TOKENIZERS_PARALLELISM=false
```
