import ast
import asyncio
import os
from pathlib import Path

import pandas as pd
from geopy.distance import geodesic
from llama_index.core.prompts import PromptTemplate
from llama_index.experimental.query_engine import (
    PandasQueryEngine as LlamaPandasQueryEngine,
)
from loguru import logger

from campus_plan_bot.interfaces.interfaces import RetrievedDocument

# This will be dynamically generated inside the class now.
# CUSTOM_PANDAS_PROMPT_TMPL = ...


class PandasQueryEngine:
    def __init__(
        self,
        df_path: str = "data/campusplan_evaluation.csv",
        user_coords_str: str | None = None,
    ):
        user_lat, user_lon = None, None
        if user_coords_str:
            try:
                coords = ast.literal_eval(user_coords_str)
                if isinstance(coords, (list, tuple)) and len(coords) == 2:
                    user_lat = float(coords[0])
                    user_lon = float(coords[1])
                else:
                    logger.warning(f"Could not parse coordinates: {user_coords_str}")
            except (ValueError, SyntaxError, TypeError) as e:
                logger.error(
                    f"Failed to parse coordinates string '{user_coords_str}': {e}"
                )

        try:
            df = pd.read_csv(df_path)
            self.df = self._preprocess_df(df, user_lat, user_lon)
        except FileNotFoundError:
            logger.error(f"DataFrame file not found at {df_path}")
            self.df = pd.DataFrame()

        prompt = self._create_dynamic_prompt(self.df)
        Path("data/prompt.txt").write_text(prompt.template)

        self.query_engine = LlamaPandasQueryEngine(
            df=self.df, verbose=True, pandas_prompt=prompt
        )

    def _create_dynamic_prompt(self, df: pd.DataFrame) -> PromptTemplate:
        """Dynamically generates a prompt template with a detailed schema
        description."""
        schema_parts = []
        for column in df.columns:
            unique_count = df[column].nunique()
            line = f"- `{column}`: Contains {unique_count} unique values."
            if unique_count > 1 and unique_count <= 5:
                unique_values = df[column].dropna().unique().tolist()
                line += f" The values are: {unique_values}"
            schema_parts.append(line)

        schema_description = (
            "Here is a description of the dataframe's schema:\n"
            + "\n".join(schema_parts)
        )

        tmpl = f"""
You are working with a pandas dataframe in Python.
The name of the dataframe is `df`.

{schema_description}

This is the result of `print(df.head())`:
{{df_str}}

If the users requests some specific information, you can query the "fakten" column using the .str.contains("...", case=False) method. You might want to put in the most promising keyword.

If the users asks about buildings near them, you can sort the dataframe by distance to the user using the "distance_meters" column (if it exists). You should also keep the distance_meters column in the final DataFrame.

If the questions translates to a complex query, avoid merging (joins) at all cost. Try to realizes this using combined boolean operators, e.g. df[df["funktion"] == "Hörsaal"] & df[df["rollstuhlgerechtigkeit"] == True].sort_values(by="distance_meters").

When you return a final DataFrame, it MUST be a subset of the original DataFrame.
The subset must only contain the columns 'identifikator' and 'name', plus any other columns that are directly relevant to answering the user's query.

Follow these instructions:
{{instruction_str}}
Query: {{query_str}}

Expression: """

        return PromptTemplate(tmpl)

    def _preprocess_df(
        self,
        df: pd.DataFrame,
        user_lat: float | None = None,
        user_lon: float | None = None,
    ) -> pd.DataFrame:
        """Preprocess the DataFrame to clean data and add new features."""
        # Remove ID column
        if "id" in df.columns:
            df = df.drop(columns=["id"])

        # Clean postal codes
        if "postleitzahl" in df.columns:
            df["postleitzahl"] = (
                df["postleitzahl"].astype(str).str.replace(".0", "", regex=False)
            )

        # transform "rollstuhlgerechtigkeit" to boolean
        if "rollstuhlgerechtigkeit" in df.columns:
            df["rollstuhlgerechtigkeit"] = df["rollstuhlgerechtigkeit"].map(
                {"yes": True, "no": False, "Not available": False, "limited": True}
            )

        # Remove column "funktion", "old_identifikator"
        if "funktion" in df.columns:
            df = df.drop(columns=["funktion"])
        if "old_identifikator" in df.columns:
            df = df.drop(columns=["old_identifikator"])

        # Calculate distance to user
        if user_lat is not None and user_lon is not None:
            user_coords = (user_lat, user_lon)

            def calculate_distance(row):
                try:
                    building_coords = map(float, ast.literal_eval(row["koordinaten"]))
                    return round(geodesic(user_coords, building_coords).meters)
                except AssertionError as e:
                    logger.error(f"Failed to calculate distance: {e}")
                    return None

            df["distance_meters"] = df.apply(calculate_distance, axis=1)

        df.fillna("Not available", inplace=True)
        return df

    async def query_df(
        self, query: str, max_results: int = 10
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
            # IMPORTANT: Pass the current state of the DataFrame to eval
            result_obj = eval(pandas_code, {"df": self.df})

            if isinstance(result_obj, pd.Series):
                result_df = result_obj.to_frame()
            elif isinstance(result_obj, pd.DataFrame):
                result_df = result_obj
            else:
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
                    id=str(
                        row["identifikator"]
                    ),  # Use index as ID since 'id' column is gone
                    data={
                        k if k != "identifikator" else "gebäude_id": v
                        for k, v in row.to_dict().items()
                    },  # replace the identifikator with gebäude_id
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

    # Example user coordinates (KIT Library) as string
    user_coords_str = "['49.01097', '8.41095']"

    engine = PandasQueryEngine(user_coords_str=user_coords_str)
    print("Preprocessed DataFrame head:")
    print(engine.df.head())

    query = "suche alle Gebäude, deren Name Infobau ist"
    results = await engine.query_df(query)

    print(f"\nQuery: '{query}'")
    if results:
        for doc in results:
            print(doc)
    else:
        print("No results found.")


if __name__ == "__main__":
    asyncio.run(main())
