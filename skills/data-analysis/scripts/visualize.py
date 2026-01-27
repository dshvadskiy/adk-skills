#!/usr/bin/env python3
"""
Generate charts and visualizations from data files.

Usage:
    python visualize.py <input_file> --type <chart_type> [--x COLUMN] [--y COLUMN] [--output chart.png]
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

try:
    import pandas as pd
    import matplotlib

    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    import seaborn as sns
except ImportError:
    logger.error("Required packages not installed. Install with: pip install pandas matplotlib seaborn")
    sys.exit(1)


# Set style
sns.set_theme(style="whitegrid")
plt.rcParams["figure.figsize"] = (10, 6)


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
        raise ValueError(f"Unsupported file format: {suffix}")


def create_histogram(df: pd.DataFrame, x: str, output: str):
    """Create histogram for a single column."""
    if x not in df.columns:
        raise ValueError(f"Column not found: {x}")

    plt.figure(figsize=(10, 6))

    # Check if numeric or categorical
    if pd.api.types.is_numeric_dtype(df[x]):
        plt.hist(df[x].dropna(), bins=30, edgecolor="black", alpha=0.7)
        plt.xlabel(x)
        plt.ylabel("Frequency")
        plt.title(f"Distribution of {x}")
    else:
        # Categorical data - use value counts
        counts = df[x].value_counts().head(20)  # Top 20 categories
        plt.bar(range(len(counts)), counts.values, alpha=0.7)
        plt.xticks(range(len(counts)), counts.index, rotation=45, ha="right")
        plt.xlabel(x)
        plt.ylabel("Count")
        plt.title(f"Distribution of {x}")

    plt.tight_layout()
    plt.savefig(output, dpi=300, bbox_inches="tight")
    logger.info(f"Saved histogram to {output}")


def create_scatter(df: pd.DataFrame, x: str, y: str, output: str):
    """Create scatter plot for two columns."""
    if x not in df.columns:
        raise ValueError(f"Column not found: {x}")
    if y not in df.columns:
        raise ValueError(f"Column not found: {y}")

    plt.figure(figsize=(10, 6))

    # Remove rows with missing values
    plot_df = df[[x, y]].dropna()

    plt.scatter(plot_df[x], plot_df[y], alpha=0.6, edgecolors="black", linewidth=0.5)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.title(f"{y} vs {x}")

    # Add trend line if both are numeric
    if pd.api.types.is_numeric_dtype(plot_df[x]) and pd.api.types.is_numeric_dtype(
        plot_df[y]
    ):
        z = np.polyfit(plot_df[x], plot_df[y], 1)
        p = np.poly1d(z)
        plt.plot(
            plot_df[x],
            p(plot_df[x]),
            "r--",
            alpha=0.8,
            label=f"Trend: y={z[0]:.2f}x+{z[1]:.2f}",
        )
        plt.legend()

    plt.tight_layout()
    plt.savefig(output, dpi=300, bbox_inches="tight")
    logger.info(f"Saved scatter plot to {output}")


def create_bar(df: pd.DataFrame, x: str, y: Optional[str], output: str):
    """Create bar chart."""
    if x not in df.columns:
        raise ValueError(f"Column not found: {x}")

    plt.figure(figsize=(10, 6))

    if y:
        # Grouped bar chart
        if y not in df.columns:
            raise ValueError(f"Column not found: {y}")

        # Aggregate data
        grouped = df.groupby(x)[y].mean().sort_values(ascending=False).head(20)
        plt.bar(range(len(grouped)), grouped.values, alpha=0.7)
        plt.xticks(range(len(grouped)), grouped.index, rotation=45, ha="right")
        plt.xlabel(x)
        plt.ylabel(f"Mean {y}")
        plt.title(f"Mean {y} by {x}")
    else:
        # Simple count bar chart
        counts = df[x].value_counts().head(20)
        plt.bar(range(len(counts)), counts.values, alpha=0.7)
        plt.xticks(range(len(counts)), counts.index, rotation=45, ha="right")
        plt.xlabel(x)
        plt.ylabel("Count")
        plt.title(f"Count by {x}")

    plt.tight_layout()
    plt.savefig(output, dpi=300, bbox_inches="tight")
    logger.info(f"Saved bar chart to {output}")


def create_line(df: pd.DataFrame, x: str, y: str, output: str):
    """Create line chart (typically for time series)."""
    if x not in df.columns:
        raise ValueError(f"Column not found: {x}")
    if y not in df.columns:
        raise ValueError(f"Column not found: {y}")

    plt.figure(figsize=(12, 6))

    # Sort by x axis
    plot_df = df[[x, y]].dropna().sort_values(x)

    plt.plot(plot_df[x], plot_df[y], marker="o", markersize=4, linewidth=2, alpha=0.7)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.title(f"{y} over {x}")
    plt.xticks(rotation=45, ha="right")
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output, dpi=300, bbox_inches="tight")
    print(f"Saved line chart to {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate charts and visualizations from data files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Chart Types:
  histogram  - Distribution of a single column
  scatter    - Relationship between two columns (requires --x and --y)
  bar        - Bar chart for categorical data (requires --x, optional --y)
  line       - Line chart for time series (requires --x and --y)

Examples:
  # Histogram of age distribution
  python visualize.py data.csv --type histogram --x age --output age_dist.png
  
  # Scatter plot of age vs salary
  python visualize.py data.csv --type scatter --x age --y salary --output age_salary.png
  
  # Bar chart of department counts
  python visualize.py data.csv --type bar --x department --output dept_counts.png
  
  # Line chart of sales over time
  python visualize.py data.csv --type line --x date --y sales --output sales_trend.png
        """,
    )

    parser.add_argument("input_file", help="Input CSV or JSON file")
    parser.add_argument(
        "--type",
        required=True,
        choices=["histogram", "scatter", "bar", "line"],
        help="Type of chart to create",
    )
    parser.add_argument("--x", help="Column for x-axis")
    parser.add_argument("--y", help="Column for y-axis")
    parser.add_argument(
        "--output", default="chart.png", help="Output file path (default: chart.png)"
    )

    args = parser.parse_args()

    # Validate required arguments
    if args.type == "histogram" and not args.x:
        parser.error("--x is required for histogram")
    if args.type in ["scatter", "line"] and (not args.x or not args.y):
        parser.error(f"--x and --y are required for {args.type}")
    if args.type == "bar" and not args.x:
        parser.error("--x is required for bar chart")

    try:
        # Load data
        df = load_data(args.input_file)
        print(f"Loaded {len(df)} rows, {len(df.columns)} columns", file=sys.stderr)

        # Create visualization
        if args.type == "histogram":
            create_histogram(df, args.x, args.output)
        elif args.type == "scatter":
            create_scatter(df, args.x, args.y, args.output)
        elif args.type == "bar":
            create_bar(df, args.x, args.y, args.output)
        elif args.type == "line":
            create_line(df, args.x, args.y, args.output)

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Import numpy here to avoid issues if not installed
    try:
        import numpy as np
    except ImportError:
        print(
            "Error: numpy is required. Install with: pip install numpy", file=sys.stderr
        )
        sys.exit(1)

    sys.exit(main())
