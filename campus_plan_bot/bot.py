import os
import re
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim

from campus_plan_bot.interfaces.interfaces import (
    LLMRequestConfig,
    MessageProtocol,
    RAGComponent,
    RetrievedDocument,
    TextBot,
)
from campus_plan_bot.interfaces.persistence_types import Conversation, Message, Role
from campus_plan_bot.llm_client import InstituteClient, LLMClient

# Other instructions that are currently not implemented:
# -	Generating navigation links to buildings using external apps (Google Maps, Apple Maps, OSM).
# -	Providing website URLs of buildings or institutes.


class LLama3PromptBuilder:
    SYSTEM_PROMPT_FALLBACK = """
    You are CampusGuide, an intelligent assistant that helps users navigate the KIT (Karlsruher Institut für Technologie) campus.
    Your responses are always concise, helpful, and in German unless the user clearly speaks another language.
    Use your internal database of building metadata (e.g. names, addresses, opening hours, accessibility, associated institutions, websites),
    enriched with OpenStreetMap and reverse geocoding information.

    Your capabilities include:
	-	Answering factual questions about buildings, such as their location, address, purpose, or opening hours.
	-	Detecting and declining requests for nonexistent or unsupported functionality.
	-	Engaging in follow-up conversation, maintaining short-term memory over a session.
    -	Using contextual info like current time to answer questions such as "Is the library open now?".

    With each user prompt, a list of retrieved documents is provided. Think before using them
    to answer, there might be only a subset of relevant documents (or even none). Don't
    provide the documents in your answer, but use the information to generate a more accurate response.
    """

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

    def format_code_message(self, code_message: str) -> str:
        return f"<|start_header_id|>ipython<|end_header_id># retrieved documents\n{code_message}<|eot_id|>"

    def format_message(self, message: MessageProtocol) -> str:
        if message.role == Role.SYSTEM:
            return self.format_system_message(message.content)
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


class RAG(RAGComponent):

    MODEL = "all-MiniLM-L6-v2"

    def __init__(self, embedding_data: list, database: pd.DataFrame):
        os.environ["TOKENIZERS_PARALLELISM"] = "true"

        self.embedding_data = embedding_data
        self.database = database
        logger.debug(f"Loading {self.MODEL} model...")
        self.model = SentenceTransformer(self.MODEL)
        logger.debug(f"Embedding {len(embedding_data)} documents...")
        self.embeddings = self.model.encode(embedding_data, convert_to_tensor=True)
        logger.debug("Embeddings loaded.")

    @classmethod
    def from_file(cls, file_path: Path) -> "RAG":
        """Create a RAG instance from a file."""
        df = pd.read_csv(file_path)
        return cls.from_df(df)

    @classmethod
    def from_df(cls, df: pd.DataFrame) -> "RAG":
        """Create a RAG instance from a DataFrame."""
        embedding_data = df["identifikator"].tolist()
        return cls(embedding_data, df)

    def retrieve_context(self, query: str, limit: int = 5) -> list[RetrievedDocument]:
        """Retrieve relevant context based on a query string."""
        # 2 step approach
        documents: list[RetrievedDocument] = []

        # 1. check whether building number of type 50.34 (1-2 numbers).(1-2 numbers) do exactly match
        PATTERN = r"(\d{1,2}\.\d{1,2})"
        mo = re.search(PATTERN, query)
        if mo:
            building_number = mo.group(0)
            logger.debug(f"Building number found: {building_number}")
            related_documents = [
                RetrievedDocument(
                    id=title,
                    content=str(self.database.iloc[index].to_dict()),
                    relevance_score=1.0,
                )
                for index, title in enumerate(self.embedding_data)
                if building_number in title
            ][:limit]
            documents.extend(related_documents)
            logger.debug(
                f"Found {len(related_documents)} documents matching the building number."
            )

        # 2. if not, use cosine similarity to find the most relevant documents
        if len(documents) < limit:
            top_k = limit - len(documents)

            query_embedding = self.model.encode(query, convert_to_tensor=True)
            cos_scores = (
                cos_sim(query_embedding, self.embeddings)[0].cpu().numpy()
            )  # does this work if data already on cpu?
            top_k_indices: Sequence[int] = np.argsort(-cos_scores)[:top_k]  # type: ignore[assignment]

            for score, index in zip(cos_scores[top_k_indices], top_k_indices):
                documents.append(
                    RetrievedDocument(
                        id=self.database.loc[index]["identifikator"],
                        content=str(self.database.iloc[index].to_dict()),
                        relevance_score=round(float(score), 3),
                    )
                )
            logger.debug(f"Found {top_k} documents using cosine similarity.")

        logger.debug(
            "Retrieved "
            + ", ".join(f"({doc.relevance_score}) {doc.id}" for doc in documents)
        )
        return documents


class SimpleTextBot(TextBot):

    def __init__(
        self,
        rag: RAG,
        prompt_builder: LLama3PromptBuilder | None = None,
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
        self.prompt_builder = prompt_builder or LLama3PromptBuilder()
        self.rag = rag

    @classmethod
    def from_file(
        cls,
        database_p: Path,
        prompt_builder: LLama3PromptBuilder | None = None,
        llm_client: LLMClient | None = None,
    ) -> "SimpleTextBot":
        # moved from init to separate method to allow to compute RAG only once and not for every bot instance
        return cls(RAG.from_file(database_p), prompt_builder, llm_client)

    def query(self, query: str) -> str:
        user_query = Message.from_content(query, Role.USER)

        documents = self.rag.retrieve_context(query, limit=5)

        rag_message = Message.from_content(
            "\n".join([str(doc) for doc in documents]), Role.USER
        )

        self.conversation_history.add_message(user_query)
        self.conversation_history.add_message(rag_message)

        prompt = self.prompt_builder.from_conversation_history(
            self.conversation_history
        )
        response = self.llm_client.query(prompt)
        self.conversation_history.add_message(
            Message.from_content(response, Role.ASSISTANT)
        )
        return response.strip()

    def reset(self) -> None:
        self.conversation_history = Conversation.new()
