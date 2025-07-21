from campus_plan_bot.interfaces.interfaces import (
    LLMClient,
    LLMRequestConfig,
    Role,
)
from campus_plan_bot.interfaces.persistence_types import Conversation, Message
from campus_plan_bot.llm_client import InstituteClient
from campus_plan_bot.prompts.prompt_builder import LLama3PromptBuilder
from campus_plan_bot.prompts.util import load_and_format_prompt


class Translator:
    def __init__(
        self,
        prompt_builder: LLama3PromptBuilder | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.prompt_builder = prompt_builder or LLama3PromptBuilder(
            load_and_format_prompt("translator_prompt")
        )
        self.llm_client = llm_client or InstituteClient(
            default_request_config=LLMRequestConfig(
                max_new_tokens=2048,  # Allow for longer translated texts
                temperature=0.01,
            )
        )

    async def translate(self, text: str, target_language: str) -> str:
        """Translates the given text to the target language."""
        # New conversation for each request since no history is needed
        conversation_history = Conversation.new()

        # Format the user message with the target language and the text to be translated
        user_content = (
            f"Translate the following text to {target_language}:\n\n---\n\n{text}"
        )
        user_message = Message.from_content(user_content, Role.USER)
        conversation_history.add_message(user_message)

        prompt = self.prompt_builder.from_conversation_history_with_system_prompt(
            conversation_history
        )
        translated_text = await self.llm_client.query_async(prompt)

        return translated_text.strip()
