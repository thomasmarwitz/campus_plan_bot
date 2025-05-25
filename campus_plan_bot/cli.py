import sys
from pathlib import Path

import click
from loguru import logger

from campus_plan_bot.bot import SimpleTextBot

database_path = Path("phase1") / "data" / "campusplan_evaluation.csv"


@click.command()
@click.option(
    "--log-level",
    default="DEBUG",
    help="Set the logging level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
)
def chat(log_level: str):
    """Simple CLI chatbot interface."""
    logger.remove()
    logger.add(sys.stderr, level=log_level.upper())

    click.echo(
        "Welcome to the chat with CampusGuide, you can ask questions about buildings, opening hours, navigation. Type 'exit' to quit."
    )
    bot = SimpleTextBot(database_path)

    while True:
        user_input: str = click.prompt("You")
        if user_input.strip().lower() in {"exit", "quit"}:
            click.echo("Goodbye!")
            break

        response = bot.query(user_input)
        click.echo(f"{bot.name}: {response}")


if __name__ == "__main__":
    chat()
