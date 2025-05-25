from pathlib import Path

import pytest


@pytest.fixture
def database_path() -> Path:
    return Path("phase1") / "data" / "campusplan_evaluation.csv"
