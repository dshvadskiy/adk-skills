---
name: data-analysis
description: Analyze CSV/JSON data files with Python scripts for statistics, visualization, and insights
version: 1.0.0
author: Agent Skills Framework
license: MIT
allowed-tools: "Bash(python:*),Bash(jq:*),Read,Write"
activation_mode: auto
max_execution_time: 300
network_access: false
python_packages:
  - pandas>=2.0.0
  - matplotlib>=3.7.0
  - seaborn>=0.12.0
  - numpy>=1.24.0
system_packages: []
compatibility: python>=3.10
metadata:
  category: data-science
  tags: csv,json,statistics,visualization,pandas
---

# Data Analysis Skill

This skill provides Python-based data analysis capabilities for CSV and JSON files. It includes scripts for data extraction, statistical analysis, and visualization.

## Available Scripts

### 1. Extract Data (`extract.py`)
Extract and filter data from CSV/JSON files with pandas.

**Usage:**
```bash
python {baseDir}/scripts/extract.py <input_file> [--columns COL1,COL2] [--filter "column==value"] [--output output.csv]
```

**Examples:**
```bash
# Extract specific columns
python {baseDir}/scripts/extract.py data.csv --columns name,age,salary

# Filter rows
python {baseDir}/scripts/extract.py data.csv --filter "age>30"

# Save to new file
python {baseDir}/scripts/extract.py data.csv --columns name,salary --output filtered.csv
```

### 2. Statistical Analysis (`stats.py`)
Calculate descriptive statistics and correlations.

**Usage:**
```bash
python {baseDir}/scripts/stats.py <input_file> [--columns COL1,COL2] [--correlations]
```

**Examples:**
```bash
# Basic statistics for all numeric columns
python {baseDir}/scripts/stats.py data.csv

# Statistics for specific columns
python {baseDir}/scripts/stats.py data.csv --columns age,salary

# Include correlation matrix
python {baseDir}/scripts/stats.py data.csv --correlations
```

### 3. Visualize Data (`visualize.py`)
Generate charts and plots from data.

**Usage:**
```bash
python {baseDir}/scripts/visualize.py <input_file> --type <chart_type> [--x COLUMN] [--y COLUMN] [--output chart.png]
```

**Chart Types:**
- `histogram`: Distribution of a single column
- `scatter`: Relationship between two columns
- `bar`: Bar chart for categorical data
- `line`: Line chart for time series

**Examples:**
```bash
# Histogram of age distribution
python {baseDir}/scripts/visualize.py data.csv --type histogram --x age --output age_dist.png

# Scatter plot of age vs salary
python {baseDir}/scripts/visualize.py data.csv --type scatter --x age --y salary --output age_salary.png

# Bar chart of category counts
python {baseDir}/scripts/visualize.py data.csv --type bar --x department --output dept_counts.png
```

## Workflow Examples

### Complete Analysis Workflow
```bash
# 1. First, examine the data structure
python {baseDir}/scripts/extract.py data.csv --columns "*"

# 2. Calculate statistics
python {baseDir}/scripts/stats.py data.csv --correlations

# 3. Create visualizations
python {baseDir}/scripts/visualize.py data.csv --type histogram --x salary --output salary_dist.png
python {baseDir}/scripts/visualize.py data.csv --type scatter --x age --y salary --output age_salary.png

# 4. Filter and export insights
python {baseDir}/scripts/extract.py data.csv --filter "salary>100000" --output high_earners.csv
```

## Supported File Formats

- **CSV**: Comma-separated values (`.csv`)
- **JSON**: JSON arrays or objects (`.json`)
- **TSV**: Tab-separated values (`.tsv`)

## Error Handling

All scripts include comprehensive error handling:
- File not found errors
- Invalid column names
- Data type mismatches
- Empty datasets
- Missing dependencies

## Dependencies

This skill requires the following Python packages:
- pandas (data manipulation)
- matplotlib (plotting)
- seaborn (statistical visualization)
- numpy (numerical operations)

Install with:
```bash
pip install pandas matplotlib seaborn numpy
```

## Security Notes

- Scripts only access files in the current working directory or subdirectories
- No network access required
- Maximum execution time: 300 seconds
- Scripts run with user permissions only

## Reference Documentation

See `references/REFERENCE.md` for detailed API documentation and advanced usage examples.
