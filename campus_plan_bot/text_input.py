import click

from campus_plan_bot.interfaces import UserInputSource


class TextInput(UserInputSource):
    """Very simple text input method."""

    def get_input(self) -> str:
        user_input: str = click.prompt(click.style("You", fg="blue"))
        return user_input
