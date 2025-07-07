from copy import copy
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
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from sentence_transformers import CrossEncoder


class RAG(RAGComponent):
    MODEL = "nomic-ai/nomic-embed-text-v1"
    RERANKER_MODEL = "ml6team/cross-encoder-mmarco-german-distilbert-base"

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
    def _normalize_text(cls, text: str) -> str:
        """Normalize text by replacing special characters with spaces."""
        return re.sub(r"[-_]", " ", text)


    @classmethod
    def from_file(cls, file_path: Path, id_column_name: str = "identifikator") -> "RAG":
        """Create a RAG instance from a file."""
        df = pd.read_csv(file_path)
        return cls.from_df(df, id_column_name)

    @classmethod
    def from_df(cls, df: pd.DataFrame, id_column_name: str = "identifikator") -> "RAG":
        """Create a RAG instance from a DataFrame."""
        documents = []
        # Ensure 'name' column exists and fill NaN with empty strings
        if "name" not in df.columns:
            df["name"] = ""
        else:
            df["name"] = df["name"].fillna("")

        for _, row in df.iterrows():
            metadata = row.to_dict()
            identifikator = str(row[id_column_name])
            name = row["name"]

            # Use name and identifikator for the document text if name is available
            text_content = f"{name} {identifikator}" if name else identifikator
            normalized_text_content = cls._normalize_text(text_content)

            doc = Document(
                text=normalized_text_content,
                metadata=metadata,
            )
            documents.append(doc)

        Settings.embed_model = HuggingFaceEmbedding(model_name=cls.MODEL, trust_remote_code=True)
        index = VectorStoreIndex.from_documents(
            documents,
        )
        return cls(index, df, id_column_name)

    def _retrieve_by_building_number(
        self, query: str
    ) -> list[RetrievedDocument]:
        """Retrieve documents by direct building number match."""

        pattern = r"(\d{1,2}\.\d{1,2}|\d+)"
        building_number_match = re.search(pattern, query)
        if not building_number_match:
            return []
        
        building_number = building_number_match.group(0)
        logger.debug(f"Building number found: {building_number}")

        matched_rows = self.database[
            self.database[self.id_column_name]
            .str.contains(building_number, na=False, regex=False)
        ]

        documents = []
        for _, row in matched_rows.iterrows():
            documents.append(
                RetrievedDocument(
                    id=row[self.id_column_name],
                    data=row.to_dict(),
                    relevance_score=1.0,
                )
            )
        logger.debug(
            f"Found {len(documents)} documents matching the building number '{building_number}' directly."
        )
        return documents
    
    def _retrieve_by_similarity(self, query: str, existing_document_ids: set[str], limit: int = 5, rerank_multiplier: int = 3) -> list[RetrievedDocument]:
        """Retrieve documents by cosine similarity and reranking."""
        existing_document_ids = copy(existing_document_ids)
        
        if len(existing_document_ids) >= limit:
            return []
    
        normalized_query = self._normalize_text(query)
        retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=limit * rerank_multiplier,  # retrieve more documents for reranking
        )
        nodes = retriever.retrieve(normalized_query)

        # Rerank the retrieved documents
        if not nodes:
            return []
    
        pairs = [(normalized_query, node.get_content()) for node in nodes]
        scores = self.reranker.predict(pairs)

        # Combine nodes with their new scores and sort
        reranked_nodes = sorted(zip(nodes, scores), key=lambda x: x[1], reverse=True)

        documents = []
        for node, score in reranked_nodes:
            doc_id = node.metadata[self.id_column_name]
            if doc_id in existing_document_ids:
                continue
            documents.append(
                RetrievedDocument(
                    id=doc_id,
                    data=node.metadata,
                    relevance_score=round(float(score), 3),
                )
            )
            existing_document_ids.add(doc_id)

        logger.debug(f"Found {len(documents)} documents using cosine similarity and reranking.")
        return documents[:limit]
    


    def retrieve_context(self, query: str, limit: int = 5) -> list[RetrievedDocument]:
        """Retrieve relevant context based on a query string."""
        documents: list[RetrievedDocument] = []

        # 1. check whether building number of type 50.34 (1-2 numbers).(1-2 numbers) do exactly match
        documents.extend(self._retrieve_by_building_number(query))

        existing_document_ids = set(doc.id for doc in documents)
        # 2. if not, use cosine similarity to find the most relevant documents
        documents.extend(self._retrieve_by_similarity(query, existing_document_ids, limit=limit - len(documents), rerank_multiplier=3))

        logger.debug(
            "Retrieved "
            + ", ".join(f"({doc.relevance_score}) {doc.id}" for doc in documents)
        )
        return documents

