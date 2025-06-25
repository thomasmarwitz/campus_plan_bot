from pathlib import Path

import pytest

from campus_plan_bot.bot import SimpleTextBot


@pytest.fixture
def bot(database_path: Path) -> SimpleTextBot:
    return SimpleTextBot()


@pytest.mark.e2e
def test_simple_multi_turn(bot: SimpleTextBot):
    """Context is preserved across multiple turns."""
    assert isinstance(bot.query("Hey, my name is Günther.", []), str)  # to fill context
    assert "Günther" in bot.query("What is my name?", [])
