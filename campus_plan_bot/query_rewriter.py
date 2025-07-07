from campus_plan_bot.bot import LLama3PromptBuilder
from campus_plan_bot.interfaces.interfaces import LLMRequestConfig
from campus_plan_bot.interfaces.persistence_types import Conversation, Message, Role
from campus_plan_bot.llm_client import InstituteClient, LLMClient


class QuestionRephraser:
    """Rephrases a user query to be more suitable for RAG."""

    REPHRASING_PROMPT_TEMPLATE = """Given a conversation history and a final user query, rephrase the user query to be more effective for a Retrieval-Augmented Generation (RAG) system. The rephrased query should resolve any implicit references or ambiguities based on the context of the conversation.

The RAG system has access to a database of buildings on a university campus.

It is of utmost importance to ONLY return the rephrased query. Do not add any other text, not even a note that you are returning the rephrased query, explanation, or greetings.

Here are some examples of how to resolve references:

Example 1:
Conversation History:
User: Ich will zur Mensa am Adenauerring.
Assistant: Die Mensa am Adenauerring hat heute von 11:00 bis 14:00 Uhr geöffnet.
User: Wann hat sie morgen auf?
Rephrased Query: Wann hat die Mensa am Adenauerring morgen auf?

Example 2:
Conversation History:
User: Wo finde ich das Institut für Angewandte und Numerische Mathematik?
Assistant: Das Institut befindet sich im Gebäude 20.30.
User: Und welche Einrichtungen sind dort noch?
Rephrased Query: Welche Einrichtungen sind im Gebäude 20.30?

Now, rephrase the final user query based on the following conversation history.

Conversation History:
{history}

User Query: "{query}"

Rephrased Query:"""

    SYSTEM_PROMPT = "You are a helpful assistant that rephrases user queries to be more effective for a retrieval system. Your goal is to convert natural language questions into concise, keyword-based queries that resolve any ambiguities from the conversation history. You MUST only output the rephrased query."

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or InstituteClient(
            default_request_config=LLMRequestConfig(
                max_new_tokens=128,
                temperature=0.1,
            )
        )

    def rephrase(self, conversation: Conversation, query: str) -> str:
        """Rephrases the user query based on conversation history."""
        history_messages = [
            msg
            for msg in conversation.messages
            if msg.role in (Role.USER, Role.ASSISTANT)
        ]


        formatted_history = []
        for message in history_messages:
            role = "User" if message.role == Role.USER else "Assistant"
            formatted_history.append(f"{role}: {message.content}")

        history_str = "\n".join(formatted_history)

        user_message = self.REPHRASING_PROMPT_TEMPLATE.format(
            history=history_str, query=query
        )

        prompt_builder = LLama3PromptBuilder(system_prompt=self.SYSTEM_PROMPT)
        prompt = prompt_builder.get_prompt(user_message)

        rephrased_query = self.llm_client.query(prompt)
        return rephrased_query.strip() 