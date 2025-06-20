import json
from typing import Callable, Protocol
from pathlib import Path

import pytest

from pydantic import BaseModel

from campus_plan_bot.interfaces import TextBot


@pytest.fixture
def database_path() -> Path:
    return Path("phase1") / "data" / "campusplan_evaluation.csv"


class Turn(BaseModel):
    input_data: str
    response_data: str
    prompt: str
    response: str


class TestCase(BaseModel):
    num_turns: int
    prompts: list[Turn]


class TestDataSet:
    def __init__(self, database_path: Path, limit: int = 10):
        self.database_path = database_path
        self.test_cases = self.load_data()[:limit]

    def load_data(self) -> list[TestCase]:
        data = json.loads(self.database_path.read_text())
        return [TestCase.model_validate(test_case) for test_case in data]


class EvalFunc(Protocol):
    def __call__(self, response: str, expected_response: str) -> float: ...


class Evaluator:

    def __init__(
        self,
        test_data_set: TestDataSet,
        bot_factory: Callable[[], TextBot],
        eval_func: EvalFunc,
    ):
        self.test_data_set = test_data_set
        self.bot_factory = bot_factory
        self.eval_func = eval_func

    def evaluate(self):
        for test_case in self.test_data_set.test_cases:
            bot = self.bot_factory()
            for turn in test_case.prompts:
                response = bot.query(turn.input_data)
                score = self.eval_func(response, turn.response)
                print(f"Score: {score}")


@pytest.fixture
def evaluator(
    test_data_set: TestDataSet, bot_factory: Callable[[], TextBot]
) -> Evaluator:
    return Evaluator(test_data_set, bot_factory)
