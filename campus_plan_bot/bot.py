from datetime import datetime

from campus_plan_bot.interfaces.interfaces import (
    LLMRequestConfig,
    MessageProtocol,
    RetrievedDocument,
    TextBot,
)
from campus_plan_bot.interfaces.persistence_types import Conversation, Message, Role
from campus_plan_bot.llm_client import InstituteClient, LLMClient

# Other instructions that are currently not implemented:
# -	Generating navigation links to buildings using external apps (Google Maps, Apple Maps, OSM).
# -	Providing website URLs of buildings or institutes.


class LLama3PromptBuilder:
    SYSTEM_PROMPT_FALLBACK = """
    You are CampusGuide, an intelligent assistant that helps users navigate the KIT (Karlsruher Institut für Technologie) campus.
    Your responses are always concise, helpful, and in German unless the user clearly speaks another language.
    Use your internal database of building metadata (e.g. names, addresses, opening hours, accessibility, associated institutions, websites),
    enriched with OpenStreetMap and reverse geocoding information.

    Your capabilities include:
	-	Answering factual questions about buildings, such as their location, address, purpose, or opening hours.
	-	Detecting and declining requests for nonexistent or unsupported functionality.
	-	Engaging in follow-up conversation, maintaining short-term memory over a session.
    -	Using contextual info like current time to answer questions such as "Is the library open now?".

    With each user prompt, a list of retrieved documents is provided. Think before using them
    to answer, there might be only a subset of relevant documents (or even none). Don't
    provide the documents in your answer, but use the information to generate a more accurate response.
    """

    SYSTEM_PROMPT_DATA_FIELDS = """
    You are CampusGuide, an intelligent assistant that helps users navigate the KIT (Karlsruher Institut für Technologie) campus.

    Your capabilities include:
	-	Answering factual questions about buildings, such as their location, address, purpose, or opening hours.
	-	Detecting and declining requests for nonexistent or unsupported functionality.
	-	Engaging in follow-up conversation, maintaining short-term memory over a session.
    -	Using contextual info like current time to answer questions such as "Is the library open now?".

    For each user query you receive a list in German language of possible types of information that are available. Your task is to decide which of the information types are necessary and relevant to answer the user's question.
    Only answer by with a json-formatted array containing a subset of the provided information types as strings. Do not include anything else in your response. Do not change the received types or add to them.
    Exclude all information types that are not strictly necessary to answer the provided question.
    """

    def __init__(self, system_prompt: str | None = None):
        self.system_prompt = system_prompt or self.SYSTEM_PROMPT_FALLBACK

    def format_system_message(self, system_message: str) -> str:
        system_information = (
            f"Today Date and Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return f"<|start_header_id|>system<|end_header_id|>{system_information}\n{system_message}<|eot_id|>"

    def format_user_message(self, user_message: str) -> str:
        return f"<|start_header_id|>user<|end_header_id|>{user_message}<|eot_id|>"

    def format_assistant_message(self, assistant_message: str) -> str:
        return (
            f"<|start_header_id|>assistant<|end_header_id>{assistant_message}<|eot_id|>"
        )

    def format_code_message(self, code_message: str) -> str:
        return f"<|start_header_id|>ipython<|end_header_id># retrieved documents\n{code_message}<|eot_id|>"

    def format_message(self, message: MessageProtocol) -> str:
        if message.role == Role.SYSTEM:
            return self.format_system_message(message.content)
        elif message.role == Role.USER:
            return self.format_user_message(message.content)
        elif message.role == Role.ASSISTANT:
            return self.format_assistant_message(message.content)
        elif message.role == Role.CODE:
            return self.format_code_message(message.content)
        else:
            raise ValueError(f"Unknown role: {message.role}")

    def get_prompt(self, user_message: str) -> str:
        system_message = self.format_system_message(self.system_prompt)
        user_message = self.format_user_message(user_message)
        return f"<|begin_of_text|>{system_message}{user_message}<|start_header_id|>assistant<|end_header_id|>"

    def from_conversation_history(
        self,
        conversation_history: Conversation,  # currently w/o system message
        system_prompt: str | None = None,
    ) -> str:
        system_message = self.format_system_message(system_prompt or self.system_prompt)

        messages = [
            self.format_message(message) for message in conversation_history.messages
        ]

        return f"<|begin_of_text|>{system_message}{''.join(messages)}<|start_header_id|>assistant<|end_header_id|>"


class SimpleTextBot(TextBot):

    def __init__(
        self,
        prompt_builder: LLama3PromptBuilder | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.name = "Bot"
        self.conversation_history = Conversation.new()
        self.llm_client = llm_client or InstituteClient(
            default_request_config=LLMRequestConfig(
                max_new_tokens=1024,
                temperature=0.3,
            )
        )
        self.prompt_builder = prompt_builder or LLama3PromptBuilder()

    def query(self, query: str, docs: list[RetrievedDocument]) -> str:
        user_query = Message.from_content(query, Role.USER)

        rag_message = Message.from_content(
            "\n".join([str(doc) for doc in docs]), Role.USER
        )

        self.conversation_history.add_message(user_query)
        self.conversation_history.add_message(rag_message)

        print(rag_message)

        prompt = self.prompt_builder.from_conversation_history(
            self.conversation_history
        )
        response = self.llm_client.query(prompt)
        self.conversation_history.add_message(
            Message.from_content(response, Role.ASSISTANT)
        )
        return response.strip()

    def reset(self) -> None:
        self.conversation_history = Conversation.new()
