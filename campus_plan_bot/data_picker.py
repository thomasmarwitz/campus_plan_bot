import json

from loguru import logger

from campus_plan_bot.bot import LLama3PromptBuilder
from campus_plan_bot.interfaces.interfaces import (
    LLMClient,
    LLMRequestConfig,
    RetrievedDocument,
    Role,
)
from campus_plan_bot.interfaces.persistence_types import Conversation, Message
from campus_plan_bot.llm_client import InstituteClient


class DataPicker:

    def __init__(
        self,
        prompt_builder: LLama3PromptBuilder | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.prompt_builder = prompt_builder or LLama3PromptBuilder(
            LLama3PromptBuilder.SYSTEM_PROMPT_DATA_FIELDS
        )
        self.llm_client = llm_client or InstituteClient(
            default_request_config=LLMRequestConfig(
                max_new_tokens=1024,
                temperature=0.3,
            )
        )

    def choose_fields(self, query: str, docs: list[RetrievedDocument]):
        """Let model choose from available fields and reduce retrieved
        documents accordingly."""
        fields = self.get_field_options(docs)
        response = self.query_model(query, fields)

        key_list = json.loads(response)
        logger.debug(f"Identified relevant fields: {key_list}")

        # remove all fields from retrieved docs that are not selected
        for doc in docs:
            doc.data = {key: doc.data[key] for key in key_list if key in doc.data}

        return docs

    def get_field_options(self, docs: list[RetrievedDocument]) -> set:
        """Find out which fields are included in the retrieved documents."""
        non_empty_keys = []
        for doc in docs:
            for key, value in doc.data.items():
                if value not in (None, "", []):
                    non_empty_keys.append(key)
        return set(non_empty_keys)

    def query_model(self, query: str, fields: set) -> str:
        """Query the model to let it select fields."""

        # new conversation for each query since no history is needed
        conversation_history = Conversation.new()

        user_query = Message.from_content(query, Role.USER)
        conversation_history.add_message(user_query)

        fields_str = f"Diese Informationstypen sind verfügbar: {fields}"
        field_query = Message.from_content(fields_str, Role.USER)
        conversation_history.add_message(field_query)

        prompt = self.prompt_builder.from_conversation_history(conversation_history)
        response = self.llm_client.query(prompt)

        return response
