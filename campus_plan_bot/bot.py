from campus_plan_bot.interfaces.interfaces import (
    LLMRequestConfig,
    MessageProtocol,
    RetrievedDocument,
    TextBot,
)
from campus_plan_bot.interfaces.persistence_types import Conversation, Message, Role
from campus_plan_bot.llm_client import InstituteClient, LLMClient


class LLama3PromptBuilder:

    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt

    def format_system_message(self, system_message: str) -> str:
        return f"<|start_header_id|>system<|end_header_id|>{system_message}<|eot_id|>"

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
        elif message.role == Role.RAG:
            return self.format_user_message(message.content)
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

        prompt = self.prompt_builder.from_conversation_history(
            self.conversation_history
        )
        response = await self.llm_client.query_async(prompt)
        self.conversation_history.add_message(
            Message.from_content(response, Role.ASSISTANT)
        )
        return response.strip()

    def reset(self) -> None:
        self.conversation_history = Conversation.new()
