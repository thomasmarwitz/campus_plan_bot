from datetime import datetime

from campus_plan_bot.interfaces import MessageProtocol, TextBot
from campus_plan_bot.llm_client import InstituteClient
from campus_plan_bot.types import Conversation, Message, Role


class LLama3PromptBuilder:
    SYSTEM_PROMPT_FALLBACK = "You are a helpful assistant. You always answer concisely (typically no more than 2-3 sentences) unless requested otherwise. You use plain text without any formatting. The only thing you can do is put an empty line between paragraphs."

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

    def format_message(self, message: MessageProtocol) -> str:
        if message.role == Role.SYSTEM:
            return self.format_system_message(message.content)
        elif message.role == Role.USER:
            return self.format_user_message(message.content)
        elif message.role == Role.ASSISTANT:
            return self.format_assistant_message(message.content)
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

    def __init__(self):
        self.name = "SimpleTextBot"
        self.conversation_history = Conversation.new()
        self.llm_client = InstituteClient()
        self.prompt_builder = LLama3PromptBuilder()

    def query(self, query: str) -> str:
        self.conversation_history.add_message(Message.from_content(query, Role.USER))
        prompt = self.prompt_builder.from_conversation_history(
            self.conversation_history
        )
        response = self.llm_client.query(prompt)
        self.conversation_history.add_message(
            Message.from_content(response, Role.ASSISTANT)
        )
        return response.strip()
