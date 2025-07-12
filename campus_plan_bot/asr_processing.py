from pathlib import Path

from loguru import logger

from campus_plan_bot.bot import LLama3PromptBuilder
from campus_plan_bot.constants import Constants
from campus_plan_bot.interfaces.interfaces import LLMClient, LLMRequestConfig, Role
from campus_plan_bot.interfaces.persistence_types import Conversation, Message
from campus_plan_bot.llm_client import InstituteClient
from campus_plan_bot.prompts.util import get_prompt


class AsrProcessor:

    def __init__(
        self,
        prompt_builder: LLama3PromptBuilder | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.prompt_builder = prompt_builder or LLama3PromptBuilder(
            get_prompt("asr_fixing")
        )
        self.llm_client = llm_client or InstituteClient(
            default_request_config=LLMRequestConfig(
                max_new_tokens=1024,
                temperature=0.01,
            )
        )

    async def fix_asr(self, input):
        """Prompt the model to create a list of ASR errors and their
        corrections."""
        # new conversation for each query since no history is needed
        conversation_history = Conversation.new()

        user_query = Message.from_content(
            f"{Constants.USER_QUERY_PRE_ASR} {input}", Role.USER
        )
        conversation_history.add_message(user_query)

        prompt = self.prompt_builder.from_conversation_history(conversation_history)
        response = await self.llm_client.query_async(prompt)

        return self.parse_response(response)

    def parse_response(self, response: str  ):
        """Apply all fixes to the input that the model identified."""

        # if something is not as expected return the partially fixed input
        try:

            response = response.replace("**", "").replace("Your Output", "").replace(":", "").replace("`", "").strip()
            return " ".join(response.split(","))

        except Exception as e:    
            logger.warning(f"Fixing ASR errors failed with error: {e} for response: '{response}'")
            logger.warning("Aborting ASR error fixing and continuing with next step.")
        return ""
