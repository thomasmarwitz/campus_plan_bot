import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from wordcloud import WordCloud


def plot_single_turn_performance_by_category(results_dir: Path, output_dir: Path):
    """Generates a grouped bar chart of single-turn performance metrics by
    category."""
    output_dir.mkdir(exist_ok=True, parents=True)

    # Find all synthetic result files
    synthetic_files = list(results_dir.glob("*_synthetic.csv"))

    if not synthetic_files:
        print("No synthetic result files found.")
        return

    category_data = {}
    for file_path in synthetic_files:
        category_name = (
            file_path.stem.replace("_synthetic", "").replace("_", " ").title()
        )
        df = pd.read_csv(file_path)

        # Calculate mean for relevant metrics
        metrics = ["FScore", "Precision", "Recall", "LLM_Judge"]
        # Check which metrics are actually in the file
        available_metrics = [m for m in metrics if m in df.columns]
        if not available_metrics:
            continue

        category_data[category_name] = df[available_metrics].mean()

    if not category_data:
        print("No data to plot.")
        return

    # Create the plot
    fig = go.Figure()

    metrics_to_plot = list(next(iter(category_data.values())).index)
    categories = list(category_data.keys())

    for metric in metrics_to_plot:
        fig.add_trace(
            go.Bar(
                name=metric,
                x=categories,
                y=[data[metric] for data in category_data.values()],
                text=[f"{data[metric]:.2f}" for data in category_data.values()],
                textposition="auto",
            )
        )

    fig.update_layout(
        barmode="group",
        title="Single-Turn Chatbot Performance by Category",
        xaxis_title="Category",
        yaxis_title="Average Score",
        yaxis=dict(range=[0, 1]),
        legend_title="Metric",
        font=dict(
            family="Courier New, monospace",
            size=14,
        ),
    )

    output_file = output_dir / "single_turn_performance_by_category.png"
    fig.write_image(str(output_file), width=1600, height=900)
    print(f"Plot saved to {output_file}")


def plot_overall_performance(results_dir: Path, output_dir: Path):
    """Generates a grouped bar chart of overall performance across major
    categories."""
    output_dir.mkdir(exist_ok=True, parents=True)

    metrics = ["FScore", "Precision", "Recall", "LLM_Judge"]
    overall_data = {}

    # 1. Aggregate all Single-Turn (Synthetic) results
    synthetic_files = list(results_dir.glob("*_synthetic.csv"))
    if synthetic_files:
        all_synthetic_df = pd.concat(
            [pd.read_csv(f) for f in synthetic_files], ignore_index=True
        )
        available_metrics = [m for m in metrics if m in all_synthetic_df.columns]
        if available_metrics:
            overall_data["Single-Turn (Synthetic)"] = all_synthetic_df[
                available_metrics
            ].mean()

    # 2. Process Multi-Turn results
    multi_turn_file = results_dir / "multi_turns.csv"
    if multi_turn_file.exists():
        df = pd.read_csv(multi_turn_file)
        available_metrics = [m for m in metrics if m in df.columns]
        if available_metrics:
            overall_data["Multi-Turn"] = df[available_metrics].mean()

    # 3. Process ASR results
    asr_files = list(results_dir.glob("local_asr_suite_*.csv"))
    for file_path in asr_files:
        if "small" in file_path.name:
            continue
        category_name = (
            file_path.stem.replace("local_asr_suite_", "ASR ").replace("_", " ").title()
        )
        df = pd.read_csv(file_path)
        available_metrics = [m for m in metrics if m in df.columns]
        if available_metrics:
            overall_data[category_name] = df[available_metrics].mean()

    if not overall_data:
        print("No data found for overall performance plot.")
        return

    # Create the plot
    fig = go.Figure()

    metrics_to_plot = list(next(iter(overall_data.values())).index)
    categories = list(overall_data.keys())

    for metric in metrics_to_plot:
        fig.add_trace(
            go.Bar(
                name=metric,
                x=categories,
                y=[data[metric] for data in overall_data.values()],
                text=[f"{data[metric]:.2f}" for data in overall_data.values()],
                textposition="auto",
            )
        )

    fig.update_layout(
        barmode="group",
        title="Overall Chatbot Performance by Evaluation Category",
        xaxis_title="Evaluation Category",
        yaxis_title="Average Score",
        yaxis=dict(range=[0, 1]),
        legend_title="Metric",
        font=dict(
            family="Courier New, monospace",
            size=14,
        ),
    )

    output_file = output_dir / "overall_performance.png"
    fig.write_image(str(output_file), width=1600, height=900)
    print(f"Plot saved to {output_file}")


def plot_multi_turn_performance_over_turns(results_dir: Path, output_dir: Path):
    """Generates a line plot of multi-turn performance metrics over
    conversation turns."""
    output_dir.mkdir(exist_ok=True, parents=True)

    multi_turn_file = results_dir / "multi_turns.csv"
    if not multi_turn_file.exists():
        print("Multi-turn results file not found.")
        return

    df = pd.read_csv(multi_turn_file)

    # Safely parse the 'metadata' column, which is a stringified JSON
    def extract_turn_idx(metadata_str):
        try:
            # The string looks like a dict, so replace single quotes if needed
            # and then load with json
            metadata = json.loads(metadata_str.replace("'", '"'))
            return metadata.get("turn_idx")
        except (json.JSONDecodeError, AttributeError):
            return None

    df["turn_idx"] = df["metadata"].apply(extract_turn_idx)

    # Drop rows where turn_idx could not be extracted
    df.dropna(subset=["turn_idx"], inplace=True)
    df["turn_idx"] = df["turn_idx"].astype(int)

    metrics = ["FScore", "Precision", "Recall", "LLM_Judge"]
    available_metrics = [m for m in metrics if m in df.columns]

    if not available_metrics:
        print("No suitable metrics found in multi-turn results.")
        return

    # Group by turn index and calculate the mean for each metric
    performance_by_turn = df.groupby("turn_idx")[available_metrics].mean()

    # Create the plot
    fig = go.Figure()

    for metric in available_metrics:
        fig.add_trace(
            go.Scatter(
                x=performance_by_turn.index,
                y=performance_by_turn[metric],
                mode="lines+markers",
                name=metric,
            )
        )

    fig.update_layout(
        title="Multi-Turn Chatbot Performance Over Conversation Turns",
        xaxis_title="Conversation Turn Index",
        yaxis_title="Average Score",
        yaxis=dict(range=[0, 1]),
        legend_title="Metric",
        font=dict(
            family="Courier New, monospace",
            size=14,
        ),
    )

    output_file = output_dir / "multi_turn_performance_over_turns.png"
    fig.write_image(str(output_file), width=1600, height=900)
    print(f"Plot saved to {output_file}")


def plot_metric_correlation_heatmap(results_dir: Path, output_dir: Path):
    """Generates a heatmap of the correlation between different evaluation
    metrics."""
    output_dir.mkdir(exist_ok=True, parents=True)

    all_files = list(results_dir.glob("*.csv"))
    if not all_files:
        print("No result files found for correlation heatmap.")
        return

    # Load and concatenate all data
    df_list = [pd.read_csv(f) for f in all_files]
    full_df = pd.concat(df_list, ignore_index=True)

    # Select only the numeric metrics for correlation
    metrics_to_correlate = [
        "FScore",
        "Precision",
        "Recall",
        "LLM_Judge",  # , 'assertions_passed_rate'
    ]

    # Filter for columns that actually exist in the dataframe
    available_metrics = [m for m in metrics_to_correlate if m in full_df.columns]

    if len(available_metrics) < 2:
        print("Not enough metric columns found to create a correlation heatmap.")
        return

    correlation_matrix = full_df[available_metrics].corr()

    # To make the color scale more meaningful, find the min and max
    # correlation values, excluding the perfect 1s on the diagonal.
    corr_values_off_diagonal = correlation_matrix.values[
        np.triu_indices_from(correlation_matrix.values, k=1)
    ]
    min_corr = corr_values_off_diagonal.min()
    max_corr = corr_values_off_diagonal.max()

    # Create the heatmap
    fig = go.Figure(
        data=go.Heatmap(
            z=correlation_matrix.values,
            x=correlation_matrix.columns,
            y=correlation_matrix.columns,
            colorscale="Viridis",
            zmin=min_corr,
            zmax=max_corr,
            text=correlation_matrix.round(2).astype(str),
            texttemplate="%{text}",
            textfont={"size": 12},
        )
    )

    fig.update_layout(
        title="Correlation Heatmap of Evaluation Metrics",
        xaxis_title="Metrics",
        yaxis_title="Metrics",
        font=dict(
            family="Courier New, monospace",
            size=14,
        ),
    )

    output_file = output_dir / "metric_correlation_heatmap.png"
    fig.write_image(str(output_file), width=1000, height=800)
    print(f"Plot saved to {output_file}")


def plot_failure_reason_wordcloud(results_dir: Path, output_dir: Path):
    """Generates a word cloud from the reasons for failed test cases."""
    output_dir.mkdir(exist_ok=True, parents=True)

    all_files = list(results_dir.glob("*.csv"))
    if not all_files:
        print("No result files found for word cloud.")
        return

    full_df = pd.concat([pd.read_csv(f) for f in all_files], ignore_index=True)

    # Filter for failures
    if "assertions_passed_rate" not in full_df.columns:
        print(
            "Column 'assertions_passed_rate' not found. Cannot generate failure word cloud."
        )
        return

    failures_df = full_df[full_df["assertions_passed_rate"] == 0]

    if failures_df.empty:
        print("No failures found. Skipping word cloud generation.")
        return

    # Combine all reasons into a single text block
    text = " ".join(reason for reason in failures_df["LLM_Judge_reason"].dropna())

    if not text.strip():
        print("No reasons found for failures. Skipping word cloud generation.")
        return

    # Generate word cloud
    wordcloud = WordCloud(
        width=1600, height=900, background_color="white", colormap="cividis"
    ).generate(text)

    # Plot and save
    plt.figure(figsize=(20, 10))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")

    output_file = output_dir / "failure_reason_wordcloud.png"
    plt.savefig(output_file, bbox_inches="tight")
    plt.close()
    print(f"Word cloud saved to {output_file}")


def escape_latex(text: str) -> str:
    """Escapes special LaTeX characters in a string."""
    if not isinstance(text, str):
        return text
    return (
        text.replace("&", r"\&")
        .replace("%", r"\%")
        .replace("$", r"\$")
        .replace("#", r"\#")
        .replace("_", r"\_")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("~", r"\textasciitilde{}")
        .replace("^", r"\textasciicircum{}")
        .replace("\\", r"\textbackslash{}")
    )


def generate_latex_report_snippets(results_dir: Path, output_dir: Path):
    """Generates a LaTeX file with example cases for different LLM judge
    scores."""
    output_dir.mkdir(exist_ok=True, parents=True)
    synthetic_files = list(results_dir.glob("*_synthetic.csv"))

    if not synthetic_files:
        print("No synthetic result files found for LaTeX snippet generation.")
        return

    latex_string = r"""
\documentclass{article}
\usepackage[a4paper, margin=1in]{geometry}
\usepackage{longtable}
\usepackage{amssymb}
\usepackage{graphicx}
\title{Chatbot Evaluation Report Snippets}
\author{Generated by evaluation framework}
\date{\today}
\begin{document}
\maketitle
"""

    for file_path in synthetic_files:
        category_name = (
            file_path.stem.replace("_synthetic", "").replace("_", " ").title()
        )
        df = pd.read_csv(file_path)

        if "LLM_Judge" not in df.columns:
            continue

        latex_string += f"\\section*{{Category: {category_name}}}\n"

        # Define score brackets
        score_brackets = {
            "Failure": df[df["LLM_Judge"] == 0],
            "Partial Success": df[(df["LLM_Judge"] > 0) & (df["LLM_Judge"] < 1)],
            "Success": df[df["LLM_Judge"] == 1],
        }

        found_any_case = False
        for title_prefix, bracket_df in score_brackets.items():
            if not bracket_df.empty:
                found_any_case = True
                case = bracket_df.iloc[0]

                score = case.get("LLM_Judge", 0)
                title = f"{title_prefix} (Score = {score:.2f})"

                latex_string += f"\\subsection*{{Example: {title}}}\n"
                latex_string += (
                    "\\begin{longtable}{p{0.2\\textwidth} p{0.8\\textwidth}}\n"
                )

                def clean_and_escape(text: str) -> str:
                    if not isinstance(text, str):
                        text = str(text)
                    cleaned_text = text.removeprefix("['").removesuffix("']")
                    return escape_latex(cleaned_text)

                # Use a dictionary to define the fields to display
                fields = {
                    "Input": clean_and_escape(case.get("input", "N/A")),
                    "Expected Output": clean_and_escape(
                        case.get("expected_output", "N/A")
                    ),
                    "Actual Output": clean_and_escape(case.get("output", "N/A")),
                    "Judge Reason": clean_and_escape(
                        case.get("LLM_Judge_reason", "N/A")
                    ),
                    "Scores": f"FScore: {case.get('FScore', 0):.2f}, Precision: {case.get('Precision', 0):.2f}, Recall: {case.get('Recall', 0):.2f}",
                }

                for field_name, field_value in fields.items():
                    latex_string += f"\\textbf{{{field_name}}} & {field_value} \\\\\n"

                latex_string += "\\end{longtable}\n"

        if not found_any_case:
            latex_string += "No representative cases found for this category.\\\\\n"

    latex_string += "\\end{document}\n"

    output_file = output_dir / "report_snippets.tex"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(latex_string)

    print(f"LaTeX report snippets saved to {output_file}")


def generate_latex_summary_table(results_dir: Path, output_dir: Path):
    """Generates a LaTeX table summarizing the number of test cases for each
    category."""
    output_dir.mkdir(exist_ok=True, parents=True)
    summary_data = {}

    # Single-turn categories
    synthetic_files = list(results_dir.glob("*_synthetic.csv"))
    for file_path in synthetic_files:
        category_name = (
            file_path.stem.replace("_synthetic", "").replace("_", " ").title()
        )
        df = pd.read_csv(file_path)
        passes = (
            df["assertions_passed_rate"].sum()
            if "assertions_passed_rate" in df.columns
            else "N/A"
        )
        summary_data[f"Single-Turn: {category_name}"] = {
            "count": len(df.index),
            "passes": passes,
        }

    # ASR categories
    asr_files = list(results_dir.glob("local_asr_suite_*.csv"))
    for file_path in asr_files:
        category_name = (
            file_path.stem.replace("local_asr_suite_", "ASR ").replace("_", " ").title()
        )
        df = pd.read_csv(file_path)
        passes = (
            df["assertions_passed_rate"].sum()
            if "assertions_passed_rate" in df.columns
            else "N/A"
        )
        summary_data[category_name] = {"count": len(df.index), "passes": passes}

    # Multi-turn category
    multi_turn_file = results_dir / "multi_turns.csv"
    if multi_turn_file.exists():
        df = pd.read_csv(multi_turn_file)
        passes = (
            df["assertions_passed_rate"].sum()
            if "assertions_passed_rate" in df.columns
            else "N/A"
        )
        summary_data["Multi-Turn"] = {"count": len(df.index), "passes": passes}

    if not summary_data:
        print("No data found to generate summary table.")
        return

    total_cases = sum(data["count"] for data in summary_data.values())  # type: ignore[misc]
    total_passes = sum(
        data["passes"]
        for data in summary_data.values()
        if isinstance(data["passes"], (int, float))
    )

    latex_string = r"""
\documentclass{article}
\usepackage[a4paper, margin=1in]{geometry}
\usepackage{booktabs}
\title{Evaluation Test Case Summary}
\author{Generated by evaluation framework}
\date{\today}
\begin{document}
\maketitle
\begin{table}[h!]
\centering
\begin{tabular}{lrr}
\toprule
\textbf{Evaluation Category} & \textbf{Test Cases} & \textbf{Assertions Passed} \\
\midrule
"""
    # Sort by category name for consistent output
    for category, data in sorted(summary_data.items()):
        latex_string += f"{category} & {data['count']} & {data['passes']} \\\\\n"

    latex_string += r"""
\midrule
\textbf{Total} & \textbf{"""
    latex_string += f"{total_cases}" + r"} & \textbf{" + f"{total_passes}"
    latex_string += r"""} \\
\bottomrule
\end{tabular}
\caption{Summary of the number of test cases and passed assertions evaluated across all categories.}
\label{tab:evaluation_summary}
\end{table}
\end{document}
"""

    output_file = output_dir / "evaluation_summary.tex"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(latex_string)

    print(f"LaTeX summary table saved to {output_file}")


if __name__ == "__main__":
    results_directory = Path("phase1/data/evaluation/results")
    output_directory = Path("docs/phase2/plots")
    plot_single_turn_performance_by_category(results_directory, output_directory)
    plot_overall_performance(results_directory, output_directory)
    plot_multi_turn_performance_over_turns(results_directory, output_directory)
    plot_metric_correlation_heatmap(results_directory, output_directory)
    plot_failure_reason_wordcloud(results_directory, output_directory)
    generate_latex_report_snippets(results_directory, output_directory)
    generate_latex_summary_table(results_directory, output_directory)
