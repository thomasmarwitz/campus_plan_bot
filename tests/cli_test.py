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


def test_cli_chat():
    runner = CliRunner()
    result = runner.invoke(chat, input="Hi\nexit\n")

    assert result.exit_code == 0
    assert "Welcome to the Chatbot CLI" in result.output
    assert "Bot:" in result.output
