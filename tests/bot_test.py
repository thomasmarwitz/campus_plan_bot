import pytest

from campus_plan_bot.bot import SimpleTextBot


@pytest.fixture
def bot():
    return SimpleTextBot()


def test_simple_bot_response(bot: SimpleTextBot):
    assert isinstance(bot.query("Hello"), str)
