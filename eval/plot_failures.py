import os

import pandas as pd
import plotly.graph_objects as go


def plot_failure_reasons(csv_path, output_path):
    """Reads failure reason data from a CSV file, creates a bar plot using
    Plotly, and saves it as a PNG image.

    Args:
        csv_path (str): The path to the input CSV file.
        output_path (str): The path to save the output PNG file.
    """
    columns_to_plot = [
        "additional information",
        "unnecessary detail",
        "unrelated information",
        "extra information",
        "incorrect",
    ]

    df = pd.read_csv(csv_path)

    for col in ["Run Name"] + columns_to_plot:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in the CSV file.")

    fig = go.Figure()

    for index, row in df.iterrows():
        run_name = row["Run Name"]
        values = row[columns_to_plot].values
        fig.add_trace(go.Bar(x=columns_to_plot, y=values, name=run_name))

    fig.update_layout(
        barmode="group",
        title="Comparison of Failure Reasons",
        xaxis_title="",
        yaxis_title="",
        legend_title="",
        xaxis_tickangle=-45,
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fig.write_image(output_path)
    print(f"Plot saved to {output_path}")


if __name__ == "__main__":
    csv_file = "docs/phase3/report/comparison-#4/failure_reason_comparison.csv"
    output_file = "docs/phase3/report/comparison-#4/failure_reason_plot.png"
    plot_failure_reasons(csv_file, output_file)
