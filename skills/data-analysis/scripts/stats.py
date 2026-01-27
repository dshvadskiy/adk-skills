#!/usr/bin/env python3
"""
Calculate descriptive statistics and correlations for data files.

Usage:
    python stats.py <input_file> [--columns COL1,COL2] [--correlations]
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
    import numpy as np
except ImportError:
    logger.error("pandas and numpy are required. Install with: pip install pandas numpy")
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
        raise ValueError(f"Unsupported file format: {suffix}")


def calculate_statistics(
    df: pd.DataFrame, columns: Optional[str] = None
) -> pd.DataFrame:
    """Calculate descriptive statistics for numeric columns."""
    if columns:
        col_list = [c.strip() for c in columns.split(",")]
        # Validate columns exist
        missing = [c for c in col_list if c not in df.columns]
        if missing:
            raise ValueError(f"Columns not found: {', '.join(missing)}")
        df = df[col_list]

    # Select only numeric columns
    numeric_df = df.select_dtypes(include=[np.number])

    if numeric_df.empty:
        raise ValueError("No numeric columns found in the data")

    # Calculate comprehensive statistics
    stats = numeric_df.describe()

    # Add additional statistics
    stats.loc["median"] = numeric_df.median()
    stats.loc["mode"] = (
        numeric_df.mode().iloc[0] if not numeric_df.mode().empty else np.nan
    )
    stats.loc["variance"] = numeric_df.var()
    stats.loc["skewness"] = numeric_df.skew()
    stats.loc["kurtosis"] = numeric_df.kurtosis()

    return stats


def calculate_correlations(
    df: pd.DataFrame, columns: Optional[str] = None
) -> pd.DataFrame:
    """Calculate correlation matrix for numeric columns."""
    if columns:
        col_list = [c.strip() for c in columns.split(",")]
        df = df[col_list]

    # Select only numeric columns
    numeric_df = df.select_dtypes(include=[np.number])

    if numeric_df.empty:
        raise ValueError("No numeric columns found for correlation")

    if len(numeric_df.columns) < 2:
        raise ValueError("Need at least 2 numeric columns for correlation")

    return numeric_df.corr()


def print_data_info(df: pd.DataFrame):
    """Print general information about the dataset."""
    logger.info("=" * 60)
    logger.info("DATASET INFORMATION")
    logger.info("=" * 60)
    logger.info(f"Rows: {len(df)}")
    logger.info(f"Columns: {len(df.columns)}")
    logger.info("\nColumn Types:")
    logger.info(df.dtypes.to_string())
    logger.info("\nMissing Values:")
    missing = df.isnull().sum()
    if missing.sum() > 0:
        logger.info(missing[missing > 0].to_string())
    else:
        logger.info("No missing values")
    logger.info("")


def main():
    parser = argparse.ArgumentParser(
        description="Calculate descriptive statistics for data files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic statistics for all numeric columns
  python stats.py data.csv
  
  # Statistics for specific columns
  python stats.py data.csv --columns age,salary,score
  
  # Include correlation matrix
  python stats.py data.csv --correlations
        """,
    )

    parser.add_argument("input_file", help="Input CSV or JSON file")
    parser.add_argument("--columns", help="Comma-separated list of columns to analyze")
    parser.add_argument(
        "--correlations", action="store_true", help="Calculate correlation matrix"
    )
    parser.add_argument(
        "--no-info", action="store_true", help="Skip dataset information output"
    )

    args = parser.parse_args()

    try:
        # Load data
        df = load_data(args.input_file)

        # Print dataset info
        if not args.no_info:
            print_data_info(df)

        # Calculate statistics
        logger.info("=" * 60)
        logger.info("DESCRIPTIVE STATISTICS")
        logger.info("=" * 60)
        stats = calculate_statistics(df, args.columns)
        logger.info(stats.to_string())
        logger.info("")

        # Calculate correlations if requested
        if args.correlations:
            logger.info("=" * 60)
            logger.info("CORRELATION MATRIX")
            logger.info("=" * 60)
            corr = calculate_correlations(df, args.columns)
            logger.info(corr.to_string())
            logger.info("")

            # Highlight strong correlations
            logger.info("Strong Correlations (|r| > 0.7):")
            strong_corr = []
            for i in range(len(corr.columns)):
                for j in range(i + 1, len(corr.columns)):
                    r = corr.iloc[i, j]
                    if abs(r) > 0.7:
                        strong_corr.append(
                            f"  {corr.columns[i]} <-> {corr.columns[j]}: {r:.3f}"
                        )

            if strong_corr:
                logger.info("\n".join(strong_corr))
            else:
                logger.info("  None found")
            logger.info("")

        return 0

    except FileNotFoundError as e:
        logger.error(f"{e}")
        return 1
    except ValueError as e:
        logger.error(f"{e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
