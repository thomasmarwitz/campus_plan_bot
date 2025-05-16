# Dialogue practical

## Installation

This installs `campus_plan_bot` as an editable Python project to enable imports from arbitrary locations inside the `campus_plan_bot` folder.

```bash
pixi run postinstall
```

## Pre-commit

We use [pre-commit](https://pre-commit.com/) to add hooks to our repo, they will run on every commit. Installation via:

```bash
pixi run pre-commit-install
```

You can run them manually with:

```bash
pixi run pre-commit-run
```

Using hooks is a good way to ensure that your code is always in a good state, e.g. code is linted, formatted, etc.

## Tests

```bash
pixi run test # this will execute our pytest suite
```
