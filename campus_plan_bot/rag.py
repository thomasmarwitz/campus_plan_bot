import re
from pathlib import Path

import pandas as pd
from loguru import logger

from campus_plan_bot.interfaces.interfaces import (
    RAGComponent,
    RetrievedDocument,
)
from llama_index.core import Document, Settings, VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


class RAG(RAGComponent):
    MODEL = "all-MiniLM-L6-v2"

    def __init__(self, index: VectorStoreIndex, database: pd.DataFrame):
        self.index = index
        self.database = database
        logger.debug("LlamaIndex RAG initialized.")

    @classmethod
    def from_file(cls, file_path: Path) -> "RAG":
        """Create a RAG instance from a file."""
        df = pd.read_csv(file_path)
        return cls.from_df(df)

    @classmethod
    def from_df(cls, df: pd.DataFrame) -> "RAG":
        """Create a RAG instance from a DataFrame."""
        documents = []
        pattern = r"(\d{1,2}\.\d{1,2})"
        for _, row in df.iterrows():
            metadata = row.to_dict()
            mo = re.search(pattern, row["title"])
            if mo:
                metadata["building_nr"] = mo.group(0)

            doc = Document(
                text=row["title"],
                metadata=metadata,
            )
            documents.append(doc)

        Settings.embed_model = HuggingFaceEmbedding(model_name=cls.MODEL)
        index = VectorStoreIndex.from_documents(
            documents,
        )
        return cls(index, df)

    def retrieve_context(self, query: str, limit: int = 5) -> list[RetrievedDocument]:
        """Retrieve relevant context based on a query string."""
        documents: list[RetrievedDocument] = []
        document_ids: set[str] = set()

        # 1. check whether building number of type 50.34 (1-2 numbers).(1-2 numbers) do exactly match
        pattern = r"(\d{1,2}\.\d{1,2})"
        mo = re.search(pattern, query)
        if mo:
            building_number = mo.group(0)
            logger.debug(f"Building number found: {building_number}")

            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=limit,
                filters=MetadataFilters(
                    filters=[
                        MetadataFilter(
                            key="building_nr",
                            value=building_number,
                        )
                    ]
                ),
            )
            nodes = retriever.retrieve(query)
            for node in nodes:
                documents.append(
                    RetrievedDocument(
                        id=node.get_content(),
                        data=node.metadata,
                        relevance_score=1.0,
                    )
                )
                document_ids.add(node.get_content())
            logger.debug(
                f"Found {len(documents)} documents matching the building number."
            )

        # 2. if not, use cosine similarity to find the most relevant documents
        if len(documents) < limit:
            top_k = limit - len(documents)

            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=top_k,
            )
            nodes = retriever.retrieve(query)

            for node in nodes:
                if node.get_content() in document_ids:
                    continue
                documents.append(
                    RetrievedDocument(
                        id=node.get_content(),
                        data=node.metadata,
                        relevance_score=round(float(node.get_score()), 3),
                    )
                )

            logger.debug(f"Found {top_k} documents using cosine similarity.")

        logger.debug(
            "Retrieved "
            + ", ".join(f"({doc.relevance_score}) {doc.id}" for doc in documents)
        )
        return documents
