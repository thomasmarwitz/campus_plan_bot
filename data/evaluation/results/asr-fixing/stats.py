from pathlib import Path
import pandas as pd

p = Path("data/evaluation/results/asr-fixing")

for path in p.glob("*.csv"):
    df = pd.read_csv(path)
    if "passed" not in df.columns:
        continue

    # only keep rows where df["original_query"] contains a number
    #df = df[df["original_query"].str.contains(r"\d\d")]

    print(f"{path.stem}: {round(df['passed'].mean(), 2)} ({df['passed'].sum()}/{len(df)})")

    if "qwen" in path.stem:
        # save all failed test cases to a file
        failed_df = df[~df["passed"]]
        failed_df.to_csv(p / (path.name + "_failed.csv"), index=False)