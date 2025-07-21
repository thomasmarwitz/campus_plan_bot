from campus_plan_bot.interfaces.interfaces import (
    LLMRequestConfig,
    RetrievedDocument,
    TextBot,
)
from campus_plan_bot.interfaces.persistence_types import Conversation, Message, Role
from campus_plan_bot.llm_client import InstituteClient, LLMClient
from campus_plan_bot.prompts.prompt_builder import LLama3PromptBuilder


class SimpleTextBot(TextBot):

    def __init__(
        self,
        prompt_builder: LLama3PromptBuilder,
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
        self.prompt_builder = prompt_builder

    async def query(self, query: str, docs: list[RetrievedDocument]):
        user_query = Message.from_content(query, Role.USER)

        rag_message = Message.from_content(
            "\n".join([str(doc) for doc in docs]), Role.RAG
        )

        self.conversation_history.add_message(user_query)
        self.conversation_history.add_message(rag_message)

        prompt = self.prompt_builder.from_conversation_history_with_system_prompt(
            self.conversation_history
        )
        response = await self.llm_client.query_async(prompt)
        self.conversation_history.add_message(
            Message.from_content(response, Role.ASSISTANT)
        )
        return response.strip()

    def reset(self) -> None:
        self.conversation_history = Conversation.new()
