import click

from campus_plan_bot.bot import SimpleTextBot


@click.command()
def chat():
    """Simple CLI chatbot interface."""
    click.echo("Welcome to the Chatbot CLI. Type 'exit' to quit.")
    bot = SimpleTextBot()

    while True:
        user_input = click.prompt("You")
        if user_input.strip().lower() in {"exit", "quit"}:
            click.echo("Goodbye!")
            break

        # Placeholder chatbot logic
        response = bot.query(user_input)
        click.echo(f"Bot: {response}")


if __name__ == "__main__":
    chat()
