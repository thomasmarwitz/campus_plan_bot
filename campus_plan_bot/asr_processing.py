from difflib import SequenceMatcher

from loguru import logger

from campus_plan_bot.bot import LLama3PromptBuilder
from campus_plan_bot.constants import Constants
from campus_plan_bot.interfaces.interfaces import LLMClient, LLMRequestConfig, Role
from campus_plan_bot.interfaces.persistence_types import Conversation, Message
from campus_plan_bot.llm_client import InstituteClient


class AsrProcessor:

    def __init__(
        self,
        prompt_builder: LLama3PromptBuilder | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.prompt_builder = prompt_builder or LLama3PromptBuilder(
            Constants.SYSTEM_PROMPT_ASR_FIX
        )
        self.llm_client = llm_client or InstituteClient(
            default_request_config=LLMRequestConfig(
                max_new_tokens=1024,
                temperature=0.01,
            )
        )

    def fix_asr(self, input):

        # new conversation for each query since no history is needed
        conversation_history = Conversation.new()

        user_query = Message.from_content(
            f"{Constants.USER_QUERY_PRE_ASR} {input}", Role.USER
        )
        conversation_history.add_message(user_query)

        prompt = self.prompt_builder.from_conversation_history(conversation_history)
        response = self.llm_client.query(prompt)

        similarity = SequenceMatcher(None, input, response).ratio()
        logger.info(
            f"Fixed ASR input. Similarity between input and correction is: {similarity}."
        )

        print(response)

        return response
