from pathlib import Path

import pytest

from campus_plan_bot.bot import SimpleTextBot
from campus_plan_bot.prompts.prompt_builder import LLama3PromptBuilder
from campus_plan_bot.prompts.util import load_and_format_prompt


@pytest.fixture
def bot(database_path: Path) -> SimpleTextBot:
    return SimpleTextBot(
        prompt_builder=LLama3PromptBuilder(
            system_prompt=load_and_format_prompt("system_prompt")
        )
    )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_simple_multi_turn(bot: SimpleTextBot):
    """Context is preserved across multiple turns."""
    assert isinstance(
        await bot.query("Hey, my name is Günther.", []), str
    )  # to fill context
    assert "Günther" in await bot.query("What is my name?", [])
