from campus_plan_bot.interfaces.interfaces import MessageProtocol, Role
from campus_plan_bot.interfaces.persistence_types import Conversation


class LLama3PromptBuilder:

    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt

    @staticmethod
    def format_system_message(system_message: str) -> str:
        return f"<|start_header_id|>system<|end_header_id|>{system_message}<|eot_id|>"

    @staticmethod
    def format_user_message(user_message: str) -> str:
        return f"<|start_header_id|>user<|end_header_id|>{user_message}<|eot_id|>"

    @staticmethod
    def format_assistant_message(assistant_message: str) -> str:
        return (
            f"<|start_header_id|>assistant<|end_header_id>{assistant_message}<|eot_id|>"
        )

    @staticmethod
    def format_code_message(code_message: str) -> str:
        return f"<|start_header_id|>ipython<|end_header_id># retrieved documents\n{code_message}<|eot_id|>"

    @staticmethod
    def format_message(message: MessageProtocol) -> str:
        if message.role == Role.SYSTEM:
            return LLama3PromptBuilder.format_system_message(message.content)
        elif message.role == Role.RAG:
            return LLama3PromptBuilder.format_user_message(message.content)
        elif message.role == Role.USER:
            return LLama3PromptBuilder.format_user_message(message.content)
        elif message.role == Role.ASSISTANT:
            return LLama3PromptBuilder.format_assistant_message(message.content)
        elif message.role == Role.CODE:
            return LLama3PromptBuilder.format_code_message(message.content)
        else:
            raise ValueError(f"Unknown role: {message.role}")

    def get_prompt(self, user_message: str) -> str:
        system_message = LLama3PromptBuilder.format_system_message(self.system_prompt)
        user_message = LLama3PromptBuilder.format_user_message(user_message)
        return f"<|begin_of_text|>{system_message}{user_message}<|start_header_id|>assistant<|end_header_id|>"

    def from_conversation_history_with_system_prompt(
        self, conversation_history: Conversation
    ) -> str:
        return self.from_conversation_history(conversation_history, self.system_prompt)

    @staticmethod
    def from_conversation_history(
        conversation_history: Conversation,  # currently w/o system message
        system_prompt: str,
    ) -> str:
        system_message = LLama3PromptBuilder.format_system_message(system_prompt)

        messages = [
            LLama3PromptBuilder.format_message(message)
            for message in conversation_history.messages
        ]

        return f"<|begin_of_text|>{system_message}{''.join(messages)}<|start_header_id|>assistant<|end_header_id|>"
