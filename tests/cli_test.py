import pytest
from click.testing import CliRunner

from campus_plan_bot.cli import chat


def parse_response(output: str) -> list[dict[str, str]]:
    # TODO: needed?
    """Parse output into sequence of {'role': str, 'content': str} dicts."""
    lines = output.splitlines()
    parsed = []
    for line in lines:
        if line.startswith("You:"):
            role = "user"
            content = line[5:]
        elif line.startswith("Bot:"):
            role = "bot"
            content = line[5:]
        else:
            role = "system"
            content = line
        parsed.append({"role": role, "content": content})
    return parsed


@pytest.mark.e2e
def test_cli_chat():
    runner = CliRunner()
    result = runner.invoke(chat, input="Wie komme ich zur Mensa?\nexit\n")

    assert result.exit_code == 0, f"The CLI should exit with code 0\n\n{result.output}"

    assert (
        "Bot:" in result.output
    ), f"There is something serious wrong with the output\n\n{result.output}"
    assert (
        "Adenauerring 7" in result.output
    ), f"The answer is not correct\n\n{result.output}"
