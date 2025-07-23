import asyncio
import json
from enum import Enum

from loguru import logger

from campus_plan_bot.clients.chute_client import ChuteModel
from campus_plan_bot.interfaces.interfaces import LLMClient
from campus_plan_bot.interfaces.persistence_types import Conversation, Role
from campus_plan_bot.prompts.prompt_builder import LLama3PromptBuilder
from campus_plan_bot.prompts.util import load_and_format_prompt


class QueryType(Enum):
    NORMAL = "normal"
    COMPLEX = "complex"


class QueryRouter:
    def __init__(
        self,
        prompt_builder: LLama3PromptBuilder | None = None,
        llm_client: LLMClient | None = None,
        allow_complex_mode: bool = True,
    ):
        self.prompt_builder = prompt_builder or LLama3PromptBuilder(
            system_prompt=load_and_format_prompt("query_router_prompt", do_format=False)
        )
        self.llm_client = llm_client or ChuteModel(no_think=True, strip_think=True)
        self.allow_complex_mode = allow_complex_mode

    async def classify_query(self, query: str, original_query: str) -> QueryType:
        """Classify the user query as normal or complex."""
        if not self.allow_complex_mode:
            return QueryType.NORMAL

        if "/complex" in original_query:
            return QueryType.COMPLEX
        if "/normal" in original_query:
            return QueryType.NORMAL

        conversation = Conversation.new()
        conversation.add_message_from_content(query, Role.USER)

        prompt = self.prompt_builder.from_conversation_history_with_system_prompt(
            conversation
        )

        response = await self.llm_client.query_async(prompt)
        response = response.strip().replace("```json", "").replace("`", "").strip()
        try:
            result = json.loads(response)
            query_type = result.get("query_type")
            return QueryType(query_type)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to classify query: {response} {e}")
            return QueryType.NORMAL


async def main():
    router = QueryRouter()
    test_queries = {
        "normal": [
            "Wo ist das Gebäude 50.34?",
            "Wann hat die Mensa zu?",
        ],
        "complex": [
            "Welche Gebäude sind für Rollstuhlfahrer zugänglich?",
            "Liste alle Institute auf, die sich auf dem Campus Nord befinden.",
        ],
    }

    for expected_type, queries in test_queries.items():
        for query in queries:
            result = await router.classify_query(query)
            print(f"Query: '{query}'")
            print(f"Expected: {expected_type}, Got: {result.value}")
            assert result.value == expected_type
            print("-" * 20)


if __name__ == "__main__":
    asyncio.run(main())
