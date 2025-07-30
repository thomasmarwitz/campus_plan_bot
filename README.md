# Dialogue practical

## Installation

This installs `campus_plan_bot` as an editable Python project to enable imports from arbitrary locations inside the `campus_plan_bot` folder.

```bash
pixi run postinstall
```

## Docker

**Build**:

```
docker build --build-arg TOKEN="..." --build-arg INSTITUTE_URL="..." -t campus-plan-bot .
```

INSTITUTE_URL can be omitted if the default URL is still working.

**Run**:

```
docker run -p 8000:8000 campus-plan-bot
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
