import os
import re
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim

from campus_plan_bot.interfaces.interfaces import (
    RAGComponent,
    RetrievedDocument,
)


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
