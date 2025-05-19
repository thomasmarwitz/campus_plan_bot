import pytest

from campus_plan_bot.bot import SimpleTextBot


@pytest.fixture
def bot():
    return SimpleTextBot()


def test_simple_bot_response(bot: SimpleTextBot):
    assert isinstance(bot.query("Hello"), str)


@pytest.mark.e2e
def test_simple_multi_turn(bot: SimpleTextBot):
    """Context is preserved across multiple turns."""
    assert isinstance(bot.query("Hey, my name is Günther."), str)  # to fill context
    assert "Günther" in bot.query("What is my name?")
