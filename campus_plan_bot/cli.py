import sys
from pathlib import Path

import click
from loguru import logger

from campus_plan_bot.asr_processing import AsrProcessor
from campus_plan_bot.bot import SimpleTextBot
from campus_plan_bot.data_picker import DataPicker
from campus_plan_bot.input.local_asr import LocalASR
from campus_plan_bot.input.remote_asr import RemoteASR
from campus_plan_bot.input.text_input import TextInput
from campus_plan_bot.interfaces.interfaces import InputMethods, UserInputSource
from campus_plan_bot.rag import RAG
from campus_plan_bot.settings.settings import Settings

database_path = Path("data") / "campusplan_evaluation.csv"


@click.command()
@click.option(
    "--log-level",
    default="DEBUG",
    help="Set the logging level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
)
@click.option(
    "--input",
    "-i",
    default="asr",
    help="Define the method to receive user input",
    type=click.Choice([input.value for input in InputMethods]),
)
@click.option(
    "--token",
    "-t",
    help="Update the input token used for authentication with remote servers",
    type=str,
)
@click.option(
    "--file",
    "-f",
    help="A file containing a voice recording used as ASR input",
    type=str,
)
def chat(log_level: str, input: str, token: str, file: str):
    """Simple CLI chatbot interface."""
    logger.remove()
    logger.add(sys.stderr, level=log_level.upper())

    # save new token to settings
    if token is not None:
        Settings().update_setting("token", token)

    # file input only works with ASR
    if file is not None and input == "text":
        logger.warning("You need to use an ASR input option when providing file inputs")
        exit(1)

    click.echo(
        "Welcome to the chat with CampusGuide, you can ask questions about buildings, opening hours, navigation. ",
        nl=False,
    )

    # prepare system components
    input_method = get_input_method(input, file)
    asr_processor = AsrProcessor()
    rag = RAG.from_file(database_path)
    data_picker = DataPicker()
    bot = SimpleTextBot()

    # start continuous turn-based conversation
    while True:

        # Step 1: get input from the user
        user_input: str = input_method.get_input()

        # input might end conversation
        if user_input.strip().lower() in {"exit", "quit"}:
            click.secho(f"{bot.name}: ", fg="cyan", nl=False)
            click.echo("Goodbye!")
            break

        # Step 2: fix ASR errors
        if input == InputMethods.ASR.value or input == InputMethods.LOCAL_ASR.value:
            fixed_input = asr_processor.fix_asr(user_input)

        # Step 3: retrieve relevant documents
        documents = rag.retrieve_context(user_input + "" + fixed_input, limit=5)

        # Step 4: select useful data fields
        documents = data_picker.choose_fields(user_input, documents)

        # Step 5: generate an answer to the query
        response = bot.query(user_input, documents)

        # Step 6: output the result
        click.secho(f"{bot.name}: ", fg="cyan", nl=False)
        click.echo(f"{response}")


def get_input_method(input_choice: str, file: str) -> UserInputSource:
    match input_choice:
        case InputMethods.TEXT.value:
            click.echo("Type 'exit' to quit.")
            return TextInput()
        case InputMethods.LOCAL_ASR.value:
            click.echo("Press 'q' to quit.")
            return LocalASR(file)
        case InputMethods.ASR.value:
            click.echo("Press 'q' to quit.")
            return RemoteASR(file)
        case _:
            click.secho(
                f"\nUnknown input method: {input_choice}. Defaulting to text input",
                fg="red",
            )
            return TextInput()


if __name__ == "__main__":
    chat()
