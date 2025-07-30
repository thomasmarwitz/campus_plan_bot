import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

from huggingface_hub import InferenceClient
from pydantic_ai import Agent
from pydantic_ai.messages import TextPart
from pydantic_ai.models import (
    Model,
    ModelMessage,
    ModelRequestParameters,
    ModelResponse,
    ModelSettings,
    StreamedResponse,
)

from campus_plan_bot.interfaces.interfaces import Role
from campus_plan_bot.interfaces.persistence_types import Conversation
from campus_plan_bot.prompts.prompt_builder import LLama3PromptBuilder

logger = logging.getLogger(__name__)

# Assuming these are defined elsewhere in your codebase
INSTITUTE_URL = (
    os.getenv("INSTITUTE_URL") or "http://hiaisc.isl.iar.kit.edu/llm_generate"
)


class InstituteModel(Model):
    """A Pydantic AI Model implementation for the Institute API."""

    def __init__(
        self,
        model_url: str = INSTITUTE_URL,
        default_max_tokens: int = 128,
        default_temperature: float = 0.3,
    ):
        self.client = InferenceClient(model=model_url)
        self.default_max_tokens = default_max_tokens
        self.default_temperature = default_temperature
        self._model_url = model_url
        logger.debug(f"InstituteModel initialized with URL: {model_url}")

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        """Make a request to the Institute model."""

        logger.debug(f"Requesting with messages: {messages}")

        # Convert messages to a single prompt string
        prompt = self._messages_to_prompt(messages)

        # Extract generation parameters
        temperature = self.default_temperature
        max_tokens = self.default_max_tokens

        if model_settings:
            if (
                "temperature" in model_settings
                and model_settings["temperature"] is not None
            ):
                temperature = model_settings["temperature"]
            if (
                "max_tokens" in model_settings
                and model_settings["max_tokens"] is not None
            ):
                max_tokens = model_settings["max_tokens"]

        try:
            # Make the request to the Institute API
            response_text = self.client.text_generation(
                prompt=prompt,
                temperature=temperature,
                max_new_tokens=max_tokens,
            )

            # If there are output tools defined, use them
            if model_request_parameters.output_tools:
                # Create a tool call using the first output tool
                tool = model_request_parameters.output_tools[0]
                from pydantic_ai.messages import ToolCallPart

                print("raw response", response_text)
                tool_call = ToolCallPart(
                    tool_name=tool.name,
                    args=response_text.strip(),
                    tool_call_id="response_1",  # Unique ID for the tool call
                )

                return ModelResponse(
                    parts=[tool_call],
                    model_name=self.model_name,
                    timestamp=datetime.now(),
                )
            else:
                # If no output tools, use function tools if available
                if model_request_parameters.function_tools:
                    tool = model_request_parameters.function_tools[0]
                    from pydantic_ai.messages import ToolCallPart

                    tool_call = ToolCallPart(
                        tool_name=tool.name,
                        args=response_text.strip(),
                        tool_call_id="response_1",
                    )

                    return ModelResponse(
                        parts=[tool_call],
                        model_name=self.model_name,
                        timestamp=datetime.now(),
                    )

                # If no tools defined, fall back to text response
                text_part = TextPart(content=response_text.strip())
                return ModelResponse(
                    parts=[text_part],
                    model_name=self.model_name,
                    timestamp=datetime.now(),
                )

        except Exception as e:
            logger.error(f"Error making request to Institute API: {e}")
            raise

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> AsyncIterator[StreamedResponse]:
        """Streaming not supported for Institute model."""
        raise NotImplementedError("Streamed requests not supported by InstituteModel")
        yield  # pragma: no cover

    @property
    def model_name(self) -> str:
        """The model name."""
        return (
            f"institute-{self._model_url.split('/')[-1]}"
            if "/" in self._model_url
            else "institute-model"
        )

    @property
    def system(self) -> str:
        """The system / model provider."""
        return "institute"

    @property
    def base_url(self) -> str | None:
        """The base URL for the provider API."""
        return self._model_url

    def _messages_to_prompt(self, messages: list[ModelMessage]) -> str:
        """Convert a list of ModelMessage objects to a single prompt string."""

        conv = Conversation.new()
        system_prompt: str | None = None
        for message in messages:
            if hasattr(message, "parts"):
                for part in message.parts:
                    if hasattr(part, "content"):
                        if hasattr(part, "part_kind"):
                            if part.part_kind == "system-prompt":
                                system_prompt = part.content
                            elif part.part_kind == "user-prompt":
                                conv.add_message_from_content(
                                    str(part.content), Role.USER
                                )
                            elif part.part_kind == "tool-return":
                                conv.add_message_from_content(
                                    str(part.content), Role.CODE
                                )
                            elif part.part_kind == "assistant-prompt":
                                conv.add_message_from_content(
                                    str(part.content), Role.ASSISTANT
                                )

        assert system_prompt is not None, "System prompt is required"

        return LLama3PromptBuilder.from_conversation_history(conv, system_prompt)


if __name__ == "__main__":
    # Example usage:
    model = InstituteModel(
        model_url=INSTITUTE_URL, default_max_tokens=512, default_temperature=0.5
    )

    # example usage with agent
    agent = Agent(
        model=model,
        system_prompt="You are a helpful assistant that uses emojis excessively.",
    )

    r = agent.run_sync(
        "What is the capital of France?",
    )
    print(r)
