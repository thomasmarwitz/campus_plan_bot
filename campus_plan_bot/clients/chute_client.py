import asyncio
import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ModelResponseStreamEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ToolCallPart,
    ToolCallPartDelta,
)
from pydantic_ai.models import (
    Model,
    ModelRequestParameters,
    ModelSettings,
    StreamedResponse,
    cached_async_http_client,
)

from campus_plan_bot.bot import LLama3PromptBuilder
from campus_plan_bot.interfaces import Role
from campus_plan_bot.persistence_types import Conversation

CHUTE_API_URL = "https://llm.chutes.ai/v1/chat/completions"


def _messages_to_chute_format(
    messages: list[ModelMessage],
) -> list[dict[str, Any]]:
    """Converts pydantic-ai messages to the Chute API format."""
    # This is a simplified converter. A real implementation would need to handle
    # different roles and content types (e.g., tool calls/responses) more robustly.
    output_messages = []
    for message in messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                # Naive role conversion
                if part.part_kind == "system-prompt":
                    output_messages.append({"role": "system", "content": part.content})
                elif part.part_kind == "user-prompt":
                    # Assuming text content for simplicity
                    output_messages.append(
                        {"role": "user", "content": str(part.content)}
                    )
                # TODO: Handle other part kinds like tool-return, retry-prompt
    return output_messages


class ChuteStreamedResponse(StreamedResponse):
    """A streaming response from the Chute API."""

    def __init__(self, response: AsyncIterator[str], model_name: str):
        super().__init__()
        self._iterator = response
        self._model_name = model_name
        self._timestamp = datetime.now()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    async def _get_event_iterator(self) -> AsyncIterator[ModelResponseStreamEvent]:
        part_index = 0
        async for line in self._iterator:
            if not line.startswith("data: "):
                continue

            data_str = line[len("data: ") :].strip()
            if data_str == "[DONE]":
                break

            try:
                chunk = json.loads(data_str)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content")
                tool_calls = delta.get("tool_calls")

                if tool_calls:
                    # Simplified: assumes one tool call per delta for clarity
                    tc_delta = tool_calls[0]
                    tc_index = tc_delta.get("index", part_index)
                    tc_id = tc_delta.get("id")
                    tc_name = tc_delta.get("function", {}).get("name")
                    tc_args = tc_delta.get("function", {}).get("arguments")

                    if tc_name:  # This is the start of a new tool call
                        part = ToolCallPart(
                            tool_name=tc_name, args=tc_args or "", tool_call_id=tc_id
                        )
                        yield PartStartEvent(index=tc_index, part=part)
                        part_index += 1
                    elif tc_args:  # This is a delta for an existing tool call
                        delta_event = ToolCallPartDelta(args_delta=tc_args)
                        yield PartDeltaEvent(index=tc_index, delta=delta_event)

                elif content:
                    # This is a text part
                    if part_index == 0:
                        # Start the first text part
                        yield PartStartEvent(
                            index=part_index, part=TextPart(content=content)
                        )
                        part_index += 1
                    else:
                        # Append to the existing text part
                        yield PartDeltaEvent(
                            index=part_index - 1,
                            delta=TextPartDelta(content_delta=content),
                        )

            except json.JSONDecodeError:
                # logger.warning(f"Failed to decode JSON from stream: {data_str}")
                continue


class ChuteModel(Model):
    """A pydantic-ai Model for the Chute API."""

    def __init__(
        self,
        model: str = "Qwen/Qwen3-32B",
        api_token: str | None = None,
        timeout: int = 120,
    ):
        self._model = model
        tok = api_token or os.getenv("CHUTES_KEY")
        assert tok, "CHUTES_KEY is not set"
        self.api_token = tok
        self.timeout = timeout

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def system(self) -> str:
        return "chute"

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": "Bearer " + self.api_token,
            "Content-Type": "application/json",
        }

    def _messages_to_prompt(self, messages: list[ModelMessage]) -> str:
        """Convert a list of ModelMessage objects to a single prompt string."""
        prompt_builder = LLama3PromptBuilder()

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

        return prompt_builder.from_conversation_history(conv, system_prompt)

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        client = cached_async_http_client(provider=self.system)
        body = {
            "model": self.model_name,
            "messages": _messages_to_chute_format(messages),
            "stream": False,
        }
        # Simplified settings application
        if model_settings and model_settings.get("max_tokens"):
            body["max_tokens"] = model_settings["max_tokens"]
        if model_settings and model_settings.get("temperature"):
            body["temperature"] = model_settings["temperature"]

        response = await client.post(
            CHUTE_API_URL,
            headers=self._build_headers(),
            json=body,
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content: str = message.get("content")

        if not content:
            raise UnexpectedModelBehavior("No content in Chute API response")

        response_text = content.strip()

        # If there are output tools defined, use them
        if model_request_parameters.output_tools:
            # Create a tool call using the first output tool
            tool = model_request_parameters.output_tools[0]

            # remove ```json{actual json}```
            response_text = (
                response_text.removeprefix("```json").removesuffix("```").strip()
            )

            tool_call = ToolCallPart(
                tool_name=tool.name,
                args=response_text,
                tool_call_id="response_1",  # Unique ID for the tool call
            )
            return ModelResponse(
                parts=[tool_call],
                model_name=self.model_name,
                timestamp=datetime.now(),
            )

        # If no output tools, use function tools if available
        if model_request_parameters.function_tools:
            tool = model_request_parameters.function_tools[0]
            tool_call = ToolCallPart(
                tool_name=tool.name,
                args=response_text,
                tool_call_id="response_1",
            )
            return ModelResponse(
                parts=[tool_call],
                model_name=self.model_name,
                timestamp=datetime.now(),
            )

        # If no tools defined, fall back to text response
        text_part = TextPart(content=response_text)
        return ModelResponse(
            parts=[text_part],
            model_name=self.model_name,
            timestamp=datetime.now(),
        )

    @asynccontextmanager
    async def request_stream(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> AsyncIterator[StreamedResponse]:
        """Perform a streaming request to the Chute API."""
        client = cached_async_http_client(provider=self.system)
        body = {
            "model": self.model_name,
            "messages": _messages_to_chute_format(messages),
            "stream": True,
        }
        if model_settings and model_settings.get("max_tokens"):
            body["max_tokens"] = model_settings["max_tokens"]
        if model_settings and model_settings.get("temperature"):
            body["temperature"] = model_settings["temperature"]

        async with client.stream(
            "POST",
            CHUTE_API_URL,
            headers=self._build_headers(),
            json=body,
            timeout=self.timeout,
        ) as response:
            response.raise_for_status()
            yield ChuteStreamedResponse(response.aiter_lines(), self.model_name)


async def main():
    """Simple test case for the ChuteModel."""
    print("--- Testing ChuteModel with run ---")
    try:
        agent = Agent(ChuteModel(model="chutesai/Mistral-Small-3.1-24B-Instruct-2503"))
        result = await agent.run("Tell me a 10-word story about a robot.")
        print("Async result:", result.output)
    except Exception as e:
        print(f"Error during async test: {e}")

    print("\n--- Testing ChuteModel with run_stream ---")
    try:
        agent_stream = Agent(ChuteModel())
        async with agent_stream.run_stream(
            "Tell me a 10-word story about a dragon."
        ) as result:
            print("Streaming result: ", end="")
            async for text in result.stream_text():
                print(text, end="", flush=True)
            print()
    except Exception as e:
        print(f"Error during stream test: {e}")


if __name__ == "__main__":
    # Ensure you have set the CHUTES_KEY environment variable
    # e.g., export CHUTES_KEY='your-api-key'
    asyncio.run(main())
