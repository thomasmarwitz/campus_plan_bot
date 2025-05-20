from pathlib import Path

import click

from campus_plan_bot.bot import SimpleTextBot

database_path = Path("phase1") / "data" / "campusplan_evaluation.csv"


@click.command()
def chat():
    """Simple CLI chatbot interface."""
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
