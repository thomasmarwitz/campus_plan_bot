import json
from copy import deepcopy

from loguru import logger

from campus_plan_bot.constants import Constants
from campus_plan_bot.interfaces.interfaces import (
    LLMClient,
    LLMRequestConfig,
    RetrievedDocument,
    Role,
)
from campus_plan_bot.interfaces.persistence_types import Conversation, Message
from campus_plan_bot.llm_client import InstituteClient
from campus_plan_bot.prompts.prompt_builder import LLama3PromptBuilder
from campus_plan_bot.prompts.util import load_and_format_prompt


class DataPicker:

    def __init__(
        self,
        prompt_builder: LLama3PromptBuilder | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.prompt_builder = prompt_builder or LLama3PromptBuilder(
            load_and_format_prompt("data_picker_prompt")
        )
        self.llm_client = llm_client or InstituteClient(
            default_request_config=LLMRequestConfig(
                max_new_tokens=512,
                temperature=0.01,
            )
        )

    async def choose_fields(self, query: str, docs: list[RetrievedDocument]):
        """Let model choose from available fields and reduce retrieved
        documents accordingly."""
        original_docs = deepcopy(docs)

        fields = self.get_field_options(docs)
        response = await self.query_model(query, fields)

        # return unmodified documents if the model response is not as expected
        try:
            key_list = json.loads(response)
            logger.debug(f"Identified relevant fields: {key_list}")

            # remove all fields from retrieved docs that are not selected
            for doc in docs:
                doc.data = {key: doc.data[key] for key in key_list if key in doc.data}
        except Exception as e:
            self.log_error(e)
            return original_docs

        return docs

    def get_field_options(self, docs: list[RetrievedDocument]) -> set:
        """Find out which fields are included in the retrieved documents."""
        non_empty_keys = []
        for doc in docs:
            for key, value in doc.data.items():
                if value not in (None, "", []):
                    non_empty_keys.append(key)
        return set(non_empty_keys)

    async def query_model(self, query: str, fields: set) -> str:
        """Query the model to let it select fields."""

        # new conversation for each query since no history is needed
        conversation_history = Conversation.new()

        user_query = Message.from_content(
            f"{Constants.USER_QUERY_PRE_FIELDS} {query}", Role.USER
        )
        conversation_history.add_message(user_query)

        fields_str = f"{Constants.AVAILABLE_FIELDS_PRE} {fields}"
        field_query = Message.from_content(fields_str, Role.USER)
        conversation_history.add_message(field_query)

        prompt = self.prompt_builder.from_conversation_history_with_system_prompt(
            conversation_history
        )
        response = await self.llm_client.query_async(prompt)

        return response

    def log_error(self, exception: Exception):
        """Something went wrong so return the unmodified documents and continue
        with the next processing step."""
        logger.error(f"Decoding model-selected fields failed with error: {exception}.")
        logger.error("Aborting field selection and continuing with next step.")
