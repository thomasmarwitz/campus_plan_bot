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

### Code Hooks and Their Purpose

- **docformatter**
  Automatically formats docstrings to follow PEP 257 conventions.

- **ruff**
  Runs a fast linter and formatter to enforce code style and catch common errors.

- **black-conda**
  Formats Python code using `black`, adapted for conda environments.

- **mypy**
  Performs static type checking to catch type-related bugs early.

- **trim trailing whitespace**
  Removes unnecessary whitespace at the end of lines.

- **fix end of files**
  Ensures files end with a newline, improving compatibility across tools.

- **check for merge conflicts**
  Detects unresolved Git merge conflict markers.

- **typos**
  Scans code for common spelling mistakes.

## Tests

```bash
pixi run test # this will execute our pytest suite
```
