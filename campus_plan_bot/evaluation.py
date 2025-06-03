import json
from typing import Callable, Protocol
from pathlib import Path

from pydantic import BaseModel

from campus_plan_bot.bot import SimpleTextBot
from loguru import logger
from campus_plan_bot.interfaces import TextBot

from bert_score import score


class Turn(BaseModel):
    input_data: str
    response_data: str | None
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
                response = bot.query(turn.prompt)
                score = self.eval_func(response, turn)
                print(f"Score: {score}")


test_data_path = (
    Path("phase1") / "data" / "evaluation" / "single_turn" / "building_category.json"
)
data_path = Path("phase1") / "data" / "campusplan_evaluation.csv"


def eval_func(response: str, turn: Turn) -> float:
    logger.debug(f"Question: {turn.prompt}")
    logger.debug(f"Response: {response}")
    logger.debug(f"Expected response: {turn.response}")
    return 1.0 if response.lower() == turn.response.lower() else 0.0


class EvalBertScore(EvalFunc):

    def __init__(self):
        # do one example score to load the model
        logger.debug("Loading BertScore model...")
        P, R, F = score(["Ich bin ein Test"], ["Ich bin ein Test"], lang="de")
        logger.debug(f"BertScore metrics for example are P: {P}, R: {R}, F: {F}")

    def __call__(self, response: str, turn: Turn) -> float:
        logger.info(f"Question: {turn.prompt}")
        logger.info(f"Response: {response}")
        logger.info(f"Expected response: {turn.response}")

        P, R, F = score([response], [turn.response], lang="de")
        logger.info(f"P: {P}, R: {R}, F: {F}")
        return F.item()


if __name__ == "__main__":
    test_data_set = TestDataSet(test_data_path, limit=1)
    evaluator = Evaluator(
        test_data_set, lambda: SimpleTextBot(data_path), EvalBertScore()
    )
    # evaluator.evaluate()
