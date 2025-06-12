import json
from io import StringIO
from pathlib import Path

import click
from bert_score import score
from loguru import logger
from pydantic import BaseModel
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext, LLMJudge
from rich.console import Console

from campus_plan_bot.bot import SimpleTextBot
from campus_plan_bot.clients.chute_client import ChuteModel

LLM_JUDGE = LLMJudge(
    rubric="Output should match expected output in meaning. It is mandatory the information is conveyed instead of listing excuses. The chatbot has access to the underlying data if the expected output also contains information. Reasoning should be concise and to the point. Format your output as a JSON object with valid quotation marks.",
    model=ChuteModel(
        model="chutesai/Mistral-Small-3.1-24B-Instruct-2503"
    ),  # requires CHUTES_KEY to be set in environment variables
    include_input=True,
    include_expected_output=True,
    score={"evaluation_name": "LLM_Judge", "include_reason": True},
)


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

    def to_cases(self) -> list[Case]:
        """Convert test cases to pydantic-evals Cases, keeping multi-turn
        conversations as single cases."""
        cases = []
        for test_idx, test_case in enumerate(self.test_cases):
            case = Case(
                name=f"{self.database_path.stem}_{test_idx+1}",
                inputs=[turn.prompt for turn in test_case.prompts],
                expected_output=[turn.response for turn in test_case.prompts],
                metadata={
                    "test_case_index": test_idx,
                    "input_data": [turn.input_data for turn in test_case.prompts],
                    "response_data": [turn.response_data for turn in test_case.prompts],
                    "num_turns": test_case.num_turns,
                    "type": self.database_path.stem,
                },
            )
            cases.append(case)
        return cases


single_turn_test_data = Path("phase1") / "data" / "evaluation" / "single_turn"
data_path = Path("phase1") / "data" / "campusplan_evaluation.csv"


class BertScoreEvaluator(Evaluator[list[str], list[str]]):
    """Evaluator that uses BertScore for comparing responses in multi-turn
    conversations."""

    def __init__(self):
        """Initialize with path to data needed for bot creation."""
        # Load BertScore model once during initialization
        logger.debug(
            f"Loading Bertscore model for {self.__class__.__name__} evaluator..."
        )
        score(["Ich bin ein Test"], ["Ich bin ein Test"], lang="de")
        logger.debug("Bertscore model loaded successfully")

    def evaluate(self, ctx: EvaluatorContext[list[str], list[str]]) -> float:
        """Evaluate a multi-turn conversation using BertScore.

        Creates a fresh bot instance for each case and evaluates each
        turn's response. Returns the average BertScore F1 score across
        all turns.
        """
        assert isinstance(ctx.output, list) and isinstance(
            ctx.expected_output, list
        ), "Output and expected output must be lists"

        assert len(ctx.output) == len(
            ctx.expected_output
        ), "Output and expected output must have the same length"

        return self.score(ctx.output, ctx.expected_output)

    def score(self, output: list[str], expected_output: list[str]) -> float: ...  # type: ignore[empty-body]


class FScore(BertScoreEvaluator):
    def score(self, output: list[str], expected_output: list[str]) -> float:
        _, _, F = score(output, expected_output, lang="de")
        return F.mean()


class Precision(BertScoreEvaluator):
    def score(self, output: list[str], expected_output: list[str]) -> float:
        P, _, _ = score(output, expected_output, lang="de")
        return P.mean()


class Recall(BertScoreEvaluator):
    def score(self, output: list[str], expected_output: list[str]) -> float:
        _, R, _ = score(output, expected_output, lang="de")
        return R.mean()


@click.command()
@click.option(
    "--test-data",
    "test_data_path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to test data directory",
    default=single_turn_test_data,
)
@click.option(
    "--data",
    "data_path",
    type=click.Path(exists=True, path_type=Path),
    default=data_path,
    help="Path to bot data directory",
)
@click.option(
    "--limit",
    type=int,
    default=1,
    help="Limit number of test cases per category (default: 1)",
)
def evaluate_bot(test_data_path: Path, data_path: Path, limit: int = 1) -> None:
    """Run evaluation using pydantic-evals framework."""

    cases = [
        case
        for file in test_data_path.glob("*synthetic.json")
        for case in TestDataSet(file, limit=limit).to_cases()
    ]

    logger.info(f"Evaluating {len(cases)} cases")

    async def bot_runner(prompts: list[str]) -> list[str]:
        bot = SimpleTextBot(data_path)
        return [bot.query(prompt) for prompt in prompts]

    dataset = Dataset(
        cases=cases, evaluators=[FScore(), Precision(), Recall(), LLM_JUDGE]
    )

    report = dataset.evaluate_sync(bot_runner)
    report.print(
        include_input=True,
        include_output=True,
        include_expected_output=True,
        include_metadata=False,
        # Not working:label_configs={"LLM_Judge": {"value_formatter": lambda x: x["reason"]}},
    )
    with open("report.txt", "w") as f:
        table = report.console_table(
            include_input=True,
            include_output=True,
            include_expected_output=True,
        )
        io_file = StringIO()
        Console(file=io_file).print(table, width=2000)
        f.write(io_file.getvalue())


if __name__ == "__main__":
    evaluate_bot()
