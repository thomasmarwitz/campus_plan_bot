import json
from pathlib import Path

import click
from bert_score import score
from loguru import logger
from pydantic import BaseModel
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import (
    EvaluationReason,
    Evaluator,
    EvaluatorContext,
    LLMJudge,
)

from campus_plan_bot.bot import RAG, SimpleTextBot
from campus_plan_bot.clients.chute_client import ChuteModel
from campus_plan_bot.reporting import report_to_df

SINGLE_TURN_LLM_JUDGE = LLMJudge(
    rubric="Output should match expected output in meaning. It is mandatory the information is conveyed instead of listing excuses. The chatbot has access to the underlying data if the expected output also contains information. Reasoning should be concise and to the point. Format your output as a JSON object with valid quotation marks.",
    model=ChuteModel(
        model="chutesai/Mistral-Small-3.1-24B-Instruct-2503"
    ),  # requires CHUTES_KEY to be set in environment variables
    include_input=True,
    include_expected_output=True,
    score={"evaluation_name": "LLM_Judge", "include_reason": True},
)

MULTI_TURN_LLM_JUDGE_EVALUATOR = LLMJudge(
    rubric="""This is an evaluation of a multi-turn conversation.
The user input is the latest prompt in a conversation.
The full conversation history up to the current turn is provided as part of the input.
The output is the chatbot's latest response.
The expected output is what a good response would be.

Please evaluate if the chatbot's response is coherent and relevant given the full conversation context.
Focus on the last answer within the total context.
The output should match the expected output in meaning.
It is mandatory that the information is conveyed instead of listing excuses.
The chatbot has access to the underlying data if the expected output also contains information.
Reasoning should be concise and to the point.
Format your output as a JSON object with valid quotation marks.
""",
    model=ChuteModel(
        model="chutesai/Mistral-Small-3.1-24B-Instruct-2503"
    ),  # requires CHUTES_KEY to be set in environment variables
    include_input=True,
    include_expected_output=True,
    score={"evaluation_name": "LLM_Judge_MultiTurn", "include_reason": True},
    assertion=False,
)


class MultiTurnLLMJudge(Evaluator[list[str], list[str]]):
    async def evaluate(
        self, ctx: EvaluatorContext[list[str], list[str]]
    ) -> EvaluationReason:
        scores = []
        reasons: list[str] = []
        for i in range(len(ctx.inputs)):
            # Construct conversation history for the current turn
            history = ""
            for j in range(i):
                history += f"User: {ctx.inputs[j]}\n"
                history += f"Bot: {ctx.output[j]}\n"

            # The 'input' for the judge is the history and the current prompt
            turn_input = f"{history}User: {ctx.inputs[i]}"

            turn_ctx = EvaluatorContext(
                name=f"turn_{i}",
                attributes={"turn_idx": i},
                metric=ctx.metrics,
                inputs=turn_input,
                output=ctx.output[i],
                expected_output=ctx.expected_output[i] if ctx.expected_output else None,
                _span_tree=ctx.span_tree,
                duration=ctx.duration,
                metadata=ctx.metadata,
            )

            result: dict = await MULTI_TURN_LLM_JUDGE_EVALUATOR.evaluate(turn_ctx)
            # The result is a dict like {'LLM_Judge_MultiTurn': EvaluationReason(value=0.8, ...)}
            # We extract the score value.
            # also extract the reason
            for key, value in result.items():
                if key.endswith("MultiTurn"):
                    if isinstance(value, EvaluationReason):
                        scores.append(float(value.value))
                        reasons.append(value.reason)
                    else:
                        scores.append(float(value))
                        reasons.append(None)
        output = EvaluationReason(
            value=sum(scores) / len(scores),
            reason="|".join(reasons),
        )
        return output


class Turn(BaseModel):
    input_data: str
    response_data: str | None
    prompt: str
    response: str
    reformulated_prompt: str | None = None
    asr_prompt: str | None = None

    def get_eval_prompt(self, asr_prompt: bool = False) -> str:
        # Logic: decide between normal or asr mode, normal mode will always use reformulated prompt if available.
        return (
            self.asr_prompt if asr_prompt else self.reformulated_prompt or self.prompt
        )


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
                name=f"{test_idx}",
                inputs=[turn.get_eval_prompt() for turn in test_case.prompts],
                expected_output=[turn.response for turn in test_case.prompts],
                metadata={"num_turns": test_case.num_turns},
            )
            cases.append(case)
        return cases


single_turn_test_data = Path("phase1") / "data" / "evaluation" / "single_turn"
multi_turn_test_data = (
    Path("phase1") / "data" / "evaluation" / "multi_turn" / "multi_turns.json"
)
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

    rag = RAG.from_file(data_path)

    cases = [
        case
        for case in TestDataSet(multi_turn_test_data, limit=limit).to_cases()
        #    for file in test_data_path.glob("*synthetic.json")
        #   for case in TestDataSet(file, limit=limit).to_cases()
    ][:1]

    logger.info(f"Evaluating {len(cases)} cases")

    async def bot_runner(prompts: list[str]) -> list[str]:
        bot = SimpleTextBot(rag)
        return [
            bot.query(prompt) for prompt in prompts
        ]  # keep conversation history during multi-turn conversations

    dataset = Dataset(
        cases=cases, evaluators=[FScore(), Precision(), Recall(), MultiTurnLLMJudge()]
    )

    report = dataset.evaluate_sync(bot_runner)
    df = report_to_df(report)
    df.to_csv("evaluation_results.csv", index=False)


if __name__ == "__main__":
    evaluate_bot()
