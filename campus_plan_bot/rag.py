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
from sentence_transformers import CrossEncoder


class RAG(RAGComponent):
    MODEL = "all-MiniLM-L6-v2"
    RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(
        self,
        index: VectorStoreIndex,
        database: pd.DataFrame,
        id_column_name: str = "identifikator",
    ):
        self.index = index
        self.database = database
        self.id_column_name = id_column_name
        self.reranker = CrossEncoder(self.RERANKER_MODEL)
        logger.debug("LlamaIndex RAG initialized.")

    @classmethod
    def from_file(cls, file_path: Path, id_column_name: str = "identifikator") -> "RAG":
        """Create a RAG instance from a file."""
        df = pd.read_csv(file_path)
        return cls.from_df(df, id_column_name)

    @classmethod
    def from_df(cls, df: pd.DataFrame, id_column_name: str = "identifikator") -> "RAG":
        """Create a RAG instance from a DataFrame."""
        documents = []
        pattern = r"(\d{1,2}\.\d{1,2}|\d+)"
        # Ensure 'name' column exists and fill NaN with empty strings
        if "name" not in df.columns:
            df["name"] = ""
        else:
            df["name"] = df["name"].fillna("")

        for _, row in df.iterrows():
            metadata = row.to_dict()
            identifikator = str(row[id_column_name])
            name = row["name"]

            mo = re.search(pattern, identifikator)
            if mo:
                metadata["building_nr"] = mo.group(0)

            # Use name and identifikator for the document text if name is available
            text_content = f"{name} ({identifikator})" if name else identifikator

            doc = Document(
                text=text_content,
                metadata=metadata,
            )
            documents.append(doc)

        Settings.embed_model = HuggingFaceEmbedding(model_name=cls.MODEL)
        index = VectorStoreIndex.from_documents(
            documents,
        )
        return cls(index, df, id_column_name)

    def retrieve_context(self, query: str, limit: int = 5) -> list[RetrievedDocument]:
        """Retrieve relevant context based on a query string."""
        documents: list[RetrievedDocument] = []
        document_ids: set[str] = set()

        # 1. check whether building number of type 50.34 (1-2 numbers).(1-2 numbers) do exactly match
        pattern = r"(\d{1,2}\.\d{1,2}|\d+)"
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
                        id=node.metadata[self.id_column_name],
                        data=node.metadata,
                        relevance_score=1.0,
                    )
                )
                document_ids.add(node.metadata[self.id_column_name])
            logger.debug(
                f"Found {len(documents)} documents matching the building number."
            )

        # 2. if not, use cosine similarity to find the most relevant documents
        if len(documents) < limit:
            top_k = limit - len(documents)
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=top_k * 3,  # retrieve more documents for reranking
            )
            nodes = retriever.retrieve(query)

            # Rerank the retrieved documents
            if nodes:
                pairs = [(query, node.get_content()) for node in nodes]
                scores = self.reranker.predict(pairs)

                # Combine nodes with their new scores and sort
                reranked_nodes = sorted(zip(nodes, scores), key=lambda x: x[1], reverse=True)

                for node, score in reranked_nodes:
                    if len(documents) >= limit:
                        break
                    doc_id = node.metadata[self.id_column_name]
                    if doc_id in document_ids:
                        continue
                    documents.append(
                        RetrievedDocument(
                            id=doc_id,
                            data=node.metadata,
                            relevance_score=round(float(score), 3),
                        )
                    )
                    document_ids.add(doc_id)

            logger.debug(f"Found {len(documents)} documents using cosine similarity and reranking.")

        logger.debug(
            "Retrieved "
            + ", ".join(f"({doc.relevance_score}) {doc.id}" for doc in documents)
        )
        return documents
