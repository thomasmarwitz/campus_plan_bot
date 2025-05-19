from campus_plan_bot.interfaces import TextBot


class SimpleTextBot(TextBot):

    def __init__(self):
        self.name = "SimpleTextBot"

    def query(self, query: str) -> str:
        # Simulate a simple text response
        return f"{self.name} received your query: {query}"
