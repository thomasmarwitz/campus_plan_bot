import asyncio
import os

import pandas as pd
from llama_index.experimental.query_engine import (
    PandasQueryEngine as LlamaPandasQueryEngine,
)
from loguru import logger

from campus_plan_bot.interfaces.interfaces import RetrievedDocument


class PandasQueryEngine:
    def __init__(self, df_path: str = "data/campusplan_evaluation.csv"):
        try:
            self.df = pd.read_csv(df_path)
            self.df.fillna("Not available", inplace=True)
        except FileNotFoundError:
            logger.error(f"DataFrame file not found at {df_path}")
            self.df = pd.DataFrame()

        self.query_engine = LlamaPandasQueryEngine(df=self.df, verbose=True)

    async def query_df(
        self, query: str, max_results: int = 15
    ) -> list[RetrievedDocument]:
        """Query the dataframe with a natural language query."""
        if self.df.empty:
            return []

        try:
            response = await asyncio.to_thread(self.query_engine.query, query)
            pandas_code = response.metadata.get("pandas_instruction_str")

            if not pandas_code:
                logger.warning("PandasQueryEngine did not return any pandas code.")
                return [
                    RetrievedDocument(
                        id="pandas_result_no_code",
                        data={"response": str(response)},
                        relevance_score=1.0,
                    )
                ]

            logger.debug(f"Executing pandas code:\n{pandas_code}")
            result_obj = eval(pandas_code, {"df": self.df})

            if isinstance(result_obj, pd.Series):
                result_df = result_obj.to_frame()
            elif isinstance(result_obj, pd.DataFrame):
                result_df = result_obj
            else:
                # If the result is not a DataFrame or Series, return it as a single document
                return [
                    RetrievedDocument(
                        id="pandas_result_other",
                        data={"response": str(result_obj)},
                        relevance_score=1.0,
                    )
                ]

            documents = []
            for _, row in result_df.head(max_results).iterrows():
                doc = RetrievedDocument(
                    id=str(row.get("id", "N/A")),
                    data=row.to_dict(),
                    relevance_score=1.0,
                )
                documents.append(doc)
            return documents

        except Exception as e:
            logger.error(f"Pandas query execution failed: {e}")
            if "response" in locals() and response:
                return [
                    RetrievedDocument(
                        id="pandas_error",
                        data={"error": str(e), "response": str(response)},
                        relevance_score=1.0,
                    )
                ]
            return []


async def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("Please set the OPENAI_API_KEY environment variable to run this example.")
        return

    engine = PandasQueryEngine()
    query = "List all buildings that have 'Mensa' in their identikator."
    results = await engine.query_df(query)

    print(f"Query: '{query}'")
    if results:
        for doc in results:
            print(doc)
    else:
        print("No results found.")


if __name__ == "__main__":
    asyncio.run(main())
