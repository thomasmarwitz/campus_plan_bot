import sys
from pathlib import Path

import click
from loguru import logger

from campus_plan_bot.bot import SimpleTextBot
from campus_plan_bot.interfaces import InputMethods, UserInputSource
from campus_plan_bot.local_asr import LocalASR
from campus_plan_bot.text_input import TextInput

database_path = Path("phase1") / "data" / "campusplan_evaluation.csv"


@click.command()
@click.option(
    "--log-level",
    default="DEBUG",
    help="Set the logging level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
)
@click.option(
    "--input",
    default=InputMethods.TEXT,
    help="Define the method to receive user input",
    type=click.Choice([input.value for input in InputMethods]),
)
def chat(log_level: str, input: str):
    """Simple CLI chatbot interface."""
    logger.remove()
    logger.add(sys.stderr, level=log_level.upper())

    bot = SimpleTextBot(database_path)

    click.echo(
        "Welcome to the chat with CampusGuide, you can ask questions about buildings, opening hours, navigation. ",
        nl=False,
    )

    input_method = get_input_method(input)

    while True:
        user_input: str = input_method.get_input()
        if user_input.strip().lower() in {"exit", "quit"}:
            click.secho(f"{bot.name}: ", fg="cyan", nl=False)
            click.echo("Goodbye!")
            break

        response = bot.query(user_input)
        click.secho(f"{bot.name}: ", fg="cyan", nl=False)
        click.echo(f"{response}")


def get_input_method(input_choice: str) -> UserInputSource:
    match input_choice:
        case InputMethods.TEXT.value:
            click.echo("Type 'exit' to quit.")
            return TextInput()
        case InputMethods.LOCAL_ASR.value:
            click.echo("Press 'q' to quit.")
            return LocalASR()
        case InputMethods.ASR.value:
            click.secho(
                "\nASR input is not supported yet. Defaulting to text input", fg="red"
            )
            return TextInput()
        case _:
            click.secho(
                f"\nUnknown input method: {input_choice}. Defaulting to text input",
                fg="red",
            )
            return TextInput()


if __name__ == "__main__":
    chat()
