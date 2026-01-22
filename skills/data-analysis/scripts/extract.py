#!/usr/bin/env python3
"""
Extract and filter data from CSV/JSON files.

Usage:
    python extract.py <input_file> [--columns COL1,COL2] [--filter "column==value"] [--output output.csv]
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

try:
    import pandas as pd
except ImportError:
    print(
        "Error: pandas is not installed. Install with: pip install pandas",
        file=sys.stderr,
    )
    sys.exit(1)


def load_data(file_path: str) -> pd.DataFrame:
    """Load data from CSV or JSON file."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(file_path)
    elif suffix == ".json":
        return pd.read_json(file_path)
    elif suffix == ".tsv":
        return pd.read_csv(file_path, sep="\t")
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use .csv, .json, or .tsv")


def filter_columns(df: pd.DataFrame, columns: Optional[str]) -> pd.DataFrame:
    """Filter dataframe to specific columns."""
    if not columns or columns == "*":
        return df

    col_list = [c.strip() for c in columns.split(",")]

    # Validate columns exist
    missing = [c for c in col_list if c not in df.columns]
    if missing:
        raise ValueError(f"Columns not found: {', '.join(missing)}")

    return df[col_list]


def filter_rows(df: pd.DataFrame, filter_expr: Optional[str]) -> pd.DataFrame:
    """Filter dataframe rows using pandas query syntax."""
    if not filter_expr:
        return df

    try:
        return df.query(filter_expr)
    except Exception as e:
        raise ValueError(f"Invalid filter expression: {filter_expr}\nError: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract and filter data from CSV/JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract specific columns
  python extract.py data.csv --columns name,age,salary
  
  # Filter rows
  python extract.py data.csv --filter "age > 30"
  
  # Combine filters and save
  python extract.py data.csv --columns name,salary --filter "salary > 50000" --output high_earners.csv
        """,
    )

    parser.add_argument("input_file", help="Input CSV or JSON file")
    parser.add_argument(
        "--columns", help="Comma-separated list of columns to extract (use * for all)"
    )
    parser.add_argument("--filter", help="Filter expression (pandas query syntax)")
    parser.add_argument("--output", help="Output file path (default: print to stdout)")
    parser.add_argument(
        "--format",
        choices=["csv", "json", "table"],
        default="csv",
        help="Output format (default: csv)",
    )

    args = parser.parse_args()

    try:
        # Load data
        df = load_data(args.input_file)
        print(f"Loaded {len(df)} rows, {len(df.columns)} columns", file=sys.stderr)

        # Filter columns
        df = filter_columns(df, args.columns)

        # Filter rows
        original_count = len(df)
        df = filter_rows(df, args.filter)
        if args.filter:
            print(
                f"Filtered to {len(df)} rows (from {original_count})", file=sys.stderr
            )

        # Output results
        if args.output:
            output_path = Path(args.output)
            if args.format == "csv" or output_path.suffix == ".csv":
                df.to_csv(args.output, index=False)
            elif args.format == "json" or output_path.suffix == ".json":
                df.to_json(args.output, orient="records", indent=2)
            else:
                df.to_csv(args.output, index=False)
            print(f"Saved to {args.output}", file=sys.stderr)
        else:
            # Print to stdout
            if args.format == "table":
                print(df.to_string(index=False))
            elif args.format == "json":
                print(df.to_json(orient="records", indent=2))
            else:
                print(df.to_csv(index=False), end="")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
