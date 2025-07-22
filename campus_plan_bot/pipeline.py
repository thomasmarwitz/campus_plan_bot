from pathlib import Path

from loguru import logger

from campus_plan_bot.asr_processing import AsrProcessor
from campus_plan_bot.bot import SimpleTextBot
from campus_plan_bot.clients.chute_client import ChuteModel
from campus_plan_bot.data_picker import DataPicker
from campus_plan_bot.interfaces.interfaces import LLMClient
from campus_plan_bot.interfaces.persistence_types import PipelineResult
from campus_plan_bot.link_extractor import (
    extract_google_maps_link,
    extract_website_link,
)
from campus_plan_bot.pandas_query_engine import PandasQueryEngine
from campus_plan_bot.prompts.prompt_builder import LLama3PromptBuilder
from campus_plan_bot.prompts.util import load_and_format_prompt
from campus_plan_bot.query_rewriter import QuestionRephraser
from campus_plan_bot.query_router import QueryRouter, QueryType
from campus_plan_bot.rag import RAG


class Pipeline:
    def __init__(
        self,
        rag: RAG,
        bot: SimpleTextBot,
        asr_processor: AsrProcessor | None = None,
        data_picker: DataPicker | None = None,
        rephraser: QuestionRephraser | None = None,
        query_router: QueryRouter | None = None,
        pandas_query_engine: PandasQueryEngine | None = None,
        user_coords_str: str | None = None,
        allow_complex_mode: bool = True,
    ):
        self.rag = rag
        self.bot = bot

        self.asr_processor = asr_processor or AsrProcessor()
        self.data_picker = data_picker or DataPicker()
        self.rephraser = rephraser or QuestionRephraser(
            ChuteModel(no_think=True, strip_think=True)  # type: ignore[arg-type]
        )
        self.query_router = query_router or QueryRouter(
            allow_complex_mode=allow_complex_mode
        )
        self.pandas_query_engine = pandas_query_engine or PandasQueryEngine(
            user_coords_str=user_coords_str
        )

    @classmethod
    def from_system_prompt(cls, llm_client: LLMClient | None = None, **kwargs):
        system_prompt = load_and_format_prompt("system_prompt")
        prompt_builder = LLama3PromptBuilder(system_prompt=system_prompt)
        bot = SimpleTextBot(prompt_builder=prompt_builder, llm_client=llm_client)
        return cls(bot=bot, **kwargs)

    @classmethod
    def from_database(cls, database_path: Path, embeddings_dir: Path, **kwargs):
        rag = RAG.from_file(database_path, persist_dir=embeddings_dir)
        return cls.from_system_prompt(rag=rag, **kwargs)

    async def run(self, user_input: str, fix_asr: bool = False) -> PipelineResult:
        # Step 1: fix ASR errors
        fixed_input = await self.asr_processor.fix_asr(user_input) if fix_asr else ""

        # Step 2: rephraser the question
        rephrased_input = await self.rephraser.rephrase(
            conversation=self.bot.conversation_history, query=user_input
        )
        logger.info(f"Rephrased input: {rephrased_input}")

        # Step 3: Classify the query
        query_type = await self.query_router.classify_query(rephrased_input, user_input)

        # Step 4: Retrieve context based on query type
        if query_type == QueryType.COMPLEX:
            # Use Pandas Query Engine for complex queries
            documents = await self.pandas_query_engine.query_df(rephrased_input)
        else:
            # Use RAG for normal queries
            documents = self.rag.retrieve_context(
                rephrased_input + " " + fixed_input, limit=5
            )
            documents = await self.data_picker.choose_fields(user_input, documents)

        # Step 5: generate an answer to the query
        response = await self.bot.query(user_input, documents)

        # Step 6: check for links in the response
        link_extraction_result = extract_google_maps_link(response)
        if link_extraction_result:
            return link_extraction_result

        # Step 7: check for other links in the response
        other_link_extraction_result = extract_website_link(response)
        if other_link_extraction_result:
            return other_link_extraction_result

        return PipelineResult(answer=response, link=None)
