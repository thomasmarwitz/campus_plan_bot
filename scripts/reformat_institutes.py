import csv
import os


def reformat_institute_names(input_file, output_file):
    """Reads a CSV file, reformats the 'identifikator' column for entries
    containing 'Institut für' at the end, and writes to a new CSV file."""
    with (
        open(input_file, newline="", encoding="utf-8") as infile,
        open(output_file, "w", newline="", encoding="utf-8") as outfile,
    ):

        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        # Write header
        header = next(reader)
        writer.writerow(header)

        # Find the index of the 'identifikator' column
        try:
            id_index = header.index("identifikator")
        except ValueError:
            print("Error: 'identifikator' column not found in the CSV file.")
            return

        for row in reader:
            identifikator = row[id_index]

            # Clean up whitespace and commas
            cleaned_id = identifikator.strip(" ,")

            suffix_to_check = ", Institut für"
            if cleaned_id.endswith(suffix_to_check):
                # Move 'Institut für' to the beginning
                base_name = cleaned_id[: -len(suffix_to_check)].strip()
                row[id_index] = f"Institut für {base_name}"
            else:
                row[id_index] = cleaned_id

            writer.writerow(row)


if __name__ == "__main__":
    input_csv = os.path.join("data", "campusplan_evaluation.csv")
    output_csv = os.path.join("data", "campusplan_evaluation_formatted.csv")
    reformat_institute_names(input_csv, output_csv)
    print(f"Processing complete. Formatted data saved to {output_csv}")
