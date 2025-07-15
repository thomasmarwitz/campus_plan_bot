import click
import pandas as pd


@click.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "--output-path",
    default="asr_fixing_failures.html",
    help="Path to save the HTML report.",
)
def visualize(input_path: str, output_path: str):
    """Generates an HTML report to visualize ASR fixing failures."""

    # --- Adjustable Settings ---
    ONLY_SHOW_FAILED = True
    ONLY_SHOW_DIFFERENT_QUERIES = True
    # -------------------------

    df = pd.read_csv(input_path)

    # Apply filters based on settings
    if ONLY_SHOW_FAILED:
        df = df[~df["passed"]]

    if ONLY_SHOW_DIFFERENT_QUERIES:
        df = df[df["original_query"] != df["fixed_query"]]

    # Start building the HTML content
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ASR Fixing Failure Analysis</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                margin: 0;
                padding: 2rem;
                background-color: #f8f9fa;
                color: #212529;
            }
            .container {
                max-width: 800px;
                margin: auto;
                background: white;
                padding: 2rem;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            h1 {
                text-align: center;
                color: #343a40;
                margin-bottom: 2rem;
            }
            .case {
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 1.5rem;
                margin-bottom: 1.5rem;
            }
            .case h2 {
                margin-top: 0;
                color: #495057;
                border-bottom: 1px solid #e9ecef;
                padding-bottom: 0.5rem;
            }
            .query {
                background-color: #e9ecef;
                border-left: 3px solid #007bff;
                padding: 0.75rem 1rem;
                border-radius: 4px;
                margin-bottom: 0.5rem;
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
                word-wrap: break-word;
            }
            .label {
                font-weight: bold;
                color: #6c757d;
                margin-top: 1rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>ASR Fixing Failure Analysis</h1>
    """

    if df.empty:
        html_content += "<p>No entries match the current filter settings.</p>"
    else:
        for i, row in enumerate(df.itertuples(index=False), 1):
            row_dict = row._asdict()
            html_content += f'<div class="case"><h2>Case {i}</h2>'
            for col_name, value in row_dict.items():
                label = col_name.replace("_", " ").title()

                # Highlight the 'passed' status in red if it's False
                is_failure = col_name == "passed" and not value
                style = 'style="border-left-color: #dc3545;"' if is_failure else ""

                html_content += f'<p class="label">{label}:</p>'
                html_content += f'<div class="query" {style}>{value}</div>'
            html_content += "</div>"

    # Close the HTML content
    html_content += """
        </div>
    </body>
    </html>
    """

    # Write the HTML file
    with open(output_path, "w") as f:
        f.write(html_content)

    click.secho(f"Report successfully generated at '{output_path}'", fg="green")


if __name__ == "__main__":
    visualize()
