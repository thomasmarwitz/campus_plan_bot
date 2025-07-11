import json
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
        """Prompt the model to create a list of ASR errors and their
        corrections."""
        # new conversation for each query since no history is needed
        conversation_history = Conversation.new()

        user_query = Message.from_content(
            f"{Constants.USER_QUERY_PRE_ASR} {input}", Role.USER
        )
        conversation_history.add_message(user_query)

        prompt = self.prompt_builder.from_conversation_history(conversation_history)
        response = self.llm_client.query(prompt)

        self.fixed_input = input

        self.apply_replacements(response)

        similarity = SequenceMatcher(None, input, self.fixed_input).ratio()
        logger.debug(
            f"Fixed ASR input. Similarity between input and correction is: {similarity}."
        )

        return self.fixed_input

    def apply_replacements(self, replacements):
        """Apply all fixes to the input that the model identified."""

        # if something is not as expected return the partially fixed input
        try:
            replacements_list = json.loads(replacements)
            self.fixed_input = replacements_list[Constants.REPLACEMENT_KEY_ORIGINAL]

            for incorrect, correct in replacements_list[
                Constants.REPLACEMENT_KEY_CORRECTION
            ].items():
                self.fixed_input = self.fixed_input.replace(incorrect, correct)

            return self.fixed_input

        except Exception as e:
            self.abort_processing(e)

    def abort_processing(self, exception: Exception):
        """Something went wrong so return the partially fixed input and
        continue with the next processing step."""
        logger.error(f"Fixing ASR errors failed with error: {exception}.")
        logger.error("Aborting ASR error fixing and continuing with next step.")
        return self.fixed_input
