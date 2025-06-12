import pandas as pd
from pydantic_evals.reporting import EvaluationReport


def expand_dict_columns(df: pd.DataFrame, columns_to_expand: list[str]) -> pd.DataFrame:
    """Expand dictionary columns in a DataFrame into individual columns with
    dotted notation.

    Parameters:
    - df: pandas DataFrame
    - columns_to_expand: list of column names containing dictionaries to expand

    Returns:
    - DataFrame with expanded columns and original dictionary columns removed
    """
    # Make a copy to avoid modifying the original DataFrame
    result_df = df.copy()

    # Track the original column order
    original_columns = list(result_df.columns)
    columns_to_drop = []

    # Process each dictionary column to expand it
    for col in columns_to_expand:
        if col not in result_df.columns:
            continue

        # Find the position of this column in the original list
        col_index = original_columns.index(col)

        # Check if the column contains dictionaries
        if result_df[col].apply(lambda x: isinstance(x, dict)).any():
            # Mark this column for dropping
            columns_to_drop.append(col)

            # Get all unique keys from the dictionaries
            all_keys: set[str] = set()
            for d in result_df[col].dropna():
                if isinstance(d, dict):
                    all_keys.update(d.keys())

            # For each key, create a new column
            new_columns = []
            for key in sorted(all_keys):
                new_col_name = f"{col}.{key}"
                result_df[new_col_name] = result_df[col].apply(
                    lambda x: x.get(key) if isinstance(x, dict) else None
                )
                new_columns.append(new_col_name)

            # Update the column order list - replace the original column with the new columns
            original_columns = (
                original_columns[:col_index]
                + new_columns
                + original_columns[col_index + 1 :]
            )

    # Drop the original dictionary columns
    result_df = result_df.drop(columns=columns_to_drop)

    # Reorder the columns to maintain original positioning with expanded columns
    final_columns = [col for col in original_columns if col in result_df.columns]
    return result_df[final_columns]


def report_to_df(report: EvaluationReport) -> pd.DataFrame:
    records = []
    for case in report.cases:
        reason = case.scores["LLM_Judge"].reason

        scores = {k: v.value for k, v in case.scores.items()}

        case_data = {
            "input": case.inputs,
            "metadata": case.metadata,
            "attributes": case.attributes,
            "expected_output": case.expected_output,
            "output": case.output,
            **scores,
            "LLM_Judge_reason": reason,
            # TODO handle scores, labels, metrics
        }

        # Calculate assertions pass rate
        assertions_total = len(case.assertions)
        assertions_passed = sum(1 for a in case.assertions.values() if a.value)
        case_data["assertions_passed_rate"] = (
            assertions_passed / assertions_total if assertions_total > 0 else 1.0
        )

        # Add individual assertion columns
        for assertion_name, assertion_obj in case.assertions.items():
            case_data[f"assertion.{assertion_name}"] = assertion_obj.value

        records.append(case_data)

    df = pd.DataFrame(records)
    df = expand_dict_columns(df, ["input", "attributes"])
    return df
