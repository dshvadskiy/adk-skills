# Data Analysis Skill - API Reference

Complete reference documentation for the data-analysis skill scripts.

## Table of Contents

1. [extract.py - Data Extraction](#extractpy---data-extraction)
2. [stats.py - Statistical Analysis](#statspy---statistical-analysis)
3. [visualize.py - Data Visualization](#visualizepy---data-visualization)
4. [Common Patterns](#common-patterns)
5. [Troubleshooting](#troubleshooting)

---

## extract.py - Data Extraction

### Purpose
Extract, filter, and transform data from CSV/JSON files using pandas.

### Command Line Interface

```bash
python extract.py <input_file> [OPTIONS]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `input_file` | Yes | Path to CSV, JSON, or TSV file |

### Options

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `--columns` | string | Comma-separated column names (use `*` for all) | `--columns name,age,salary` |
| `--filter` | string | Pandas query expression for row filtering | `--filter "age > 30 and salary < 100000"` |
| `--output` | string | Output file path (stdout if omitted) | `--output filtered.csv` |
| `--format` | choice | Output format: csv, json, table | `--format json` |

### Filter Expression Syntax

The `--filter` option uses pandas query syntax:

**Comparison Operators:**
- `==` (equal), `!=` (not equal)
- `>`, `>=`, `<`, `<=`
- `in`, `not in`

**Logical Operators:**
- `and`, `or`, `not`

**Examples:**
```bash
# Single condition
--filter "age > 30"

# Multiple conditions
--filter "age > 30 and salary < 100000"

# String matching
--filter "department == 'Engineering'"

# List membership
--filter "status in ['active', 'pending']"

# Complex expressions
--filter "(age > 30 or experience > 5) and salary > 50000"
```

### Output Formats

**CSV (default):**
```bash
python extract.py data.csv --columns name,age
# Output: name,age\nJohn,30\nJane,25
```

**JSON:**
```bash
python extract.py data.csv --format json
# Output: [{"name": "John", "age": 30}, {"name": "Jane", "age": 25}]
```

**Table (human-readable):**
```bash
python extract.py data.csv --format table
# Output: Formatted ASCII table
```

### Examples

**Extract specific columns:**
```bash
python extract.py employees.csv --columns employee_id,name,department,salary
```

**Filter high earners:**
```bash
python extract.py employees.csv --filter "salary > 100000" --output high_earners.csv
```

**Complex filtering:**
```bash
python extract.py employees.csv \
  --columns name,age,department,salary \
  --filter "department == 'Engineering' and age < 40" \
  --output young_engineers.csv
```

**JSON output:**
```bash
python extract.py data.csv --format json --output data.json
```

### Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `File not found` | Input file doesn't exist | Check file path |
| `Columns not found` | Invalid column names | Use `--columns *` to see all columns |
| `Invalid filter expression` | Syntax error in filter | Check pandas query syntax |
| `Unsupported file format` | Wrong file extension | Use .csv, .json, or .tsv |

---

## stats.py - Statistical Analysis

### Purpose
Calculate comprehensive descriptive statistics and correlation analysis.

### Command Line Interface

```bash
python stats.py <input_file> [OPTIONS]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `input_file` | Yes | Path to CSV, JSON, or TSV file |

### Options

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `--columns` | string | Comma-separated column names to analyze | `--columns age,salary,score` |
| `--correlations` | flag | Calculate correlation matrix | `--correlations` |
| `--no-info` | flag | Skip dataset information output | `--no-info` |

### Statistics Calculated

**Basic Statistics (from pandas describe):**
- count: Number of non-null values
- mean: Average value
- std: Standard deviation
- min: Minimum value
- 25%: First quartile
- 50%: Median (also calculated separately)
- 75%: Third quartile
- max: Maximum value

**Additional Statistics:**
- median: Middle value
- mode: Most frequent value
- variance: Measure of spread
- skewness: Asymmetry of distribution
- kurtosis: Tailedness of distribution

### Correlation Analysis

When `--correlations` flag is used:
- Pearson correlation coefficient between all numeric columns
- Range: -1 (perfect negative) to +1 (perfect positive)
- Highlights strong correlations (|r| > 0.7)

### Output Format

```
==============================================================
DATASET INFORMATION
==============================================================
Rows: 1000
Columns: 5

Column Types:
name        object
age          int64
salary     float64
department  object
score      float64

Missing Values:
No missing values

==============================================================
DESCRIPTIVE STATISTICS
==============================================================
              age       salary        score
count    1000.000    1000.000    1000.000
mean       35.234   75234.567      82.456
std         8.123   15234.890      12.345
min        22.000   45000.000      50.000
25%        29.000   65000.000      75.000
50%        35.000   75000.000      83.000
75%        41.000   85000.000      91.000
max        58.000  125000.000      99.000
median     35.000   75000.000      83.000
mode       34.000   70000.000      85.000
variance   65.987  232101234.567     152.398
skewness    0.123       0.456      -0.234
kurtosis   -0.234       0.123       0.456

==============================================================
CORRELATION MATRIX
==============================================================
           age    salary     score
age      1.000     0.654     0.123
salary   0.654     1.000     0.234
score    0.123     0.234     1.000

Strong Correlations (|r| > 0.7):
  None found
```

### Examples

**Basic statistics for all columns:**
```bash
python stats.py employees.csv
```

**Statistics for specific columns:**
```bash
python stats.py employees.csv --columns age,salary,years_experience
```

**Include correlation analysis:**
```bash
python stats.py employees.csv --correlations
```

**Minimal output (no dataset info):**
```bash
python stats.py employees.csv --no-info --correlations
```

### Interpreting Results

**Skewness:**
- Near 0: Symmetric distribution
- Positive: Right-skewed (tail on right)
- Negative: Left-skewed (tail on left)

**Kurtosis:**
- Near 0: Normal distribution
- Positive: Heavy tails (more outliers)
- Negative: Light tails (fewer outliers)

**Correlation:**
- |r| > 0.7: Strong correlation
- 0.3 < |r| < 0.7: Moderate correlation
- |r| < 0.3: Weak correlation

---

## visualize.py - Data Visualization

### Purpose
Generate publication-quality charts and plots from data files.

### Command Line Interface

```bash
python visualize.py <input_file> --type <chart_type> [OPTIONS]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `input_file` | Yes | Path to CSV, JSON, or TSV file |
| `--type` | Yes | Chart type: histogram, scatter, bar, line |

### Options

| Option | Type | Description | Required For |
|--------|------|-------------|--------------|
| `--x` | string | Column for x-axis | All chart types |
| `--y` | string | Column for y-axis | scatter, line |
| `--output` | string | Output file path (default: chart.png) | Optional |

### Chart Types

#### 1. Histogram

**Purpose:** Show distribution of a single variable

**Required:** `--x`

**Example:**
```bash
python visualize.py data.csv --type histogram --x age --output age_distribution.png
```

**Features:**
- Automatic binning (30 bins for numeric data)
- Handles categorical data (shows value counts)
- Limits to top 20 categories for readability

#### 2. Scatter Plot

**Purpose:** Show relationship between two numeric variables

**Required:** `--x`, `--y`

**Example:**
```bash
python visualize.py data.csv --type scatter --x age --y salary --output age_vs_salary.png
```

**Features:**
- Automatic trend line (linear regression)
- Displays equation: y = mx + b
- Removes missing values automatically

#### 3. Bar Chart

**Purpose:** Compare categories or show aggregated data

**Required:** `--x`

**Optional:** `--y` (for aggregation)

**Examples:**
```bash
# Simple count bar chart
python visualize.py data.csv --type bar --x department --output dept_counts.png

# Aggregated bar chart (mean salary by department)
python visualize.py data.csv --type bar --x department --y salary --output avg_salary_by_dept.png
```

**Features:**
- Limits to top 20 categories
- Automatic sorting by value
- Handles both count and aggregation modes

#### 4. Line Chart

**Purpose:** Show trends over time or ordered data

**Required:** `--x`, `--y`

**Example:**
```bash
python visualize.py sales.csv --type line --x date --y revenue --output sales_trend.png
```

**Features:**
- Automatic sorting by x-axis
- Grid lines for readability
- Markers at data points

### Output Specifications

- **Format:** PNG (high quality)
- **Resolution:** 300 DPI (publication quality)
- **Size:** 10x6 inches (default)
- **Style:** Seaborn whitegrid theme

### Examples

**Age distribution:**
```bash
python visualize.py employees.csv --type histogram --x age --output age_dist.png
```

**Salary vs experience:**
```bash
python visualize.py employees.csv --type scatter --x years_experience --y salary --output exp_salary.png
```

**Department headcount:**
```bash
python visualize.py employees.csv --type bar --x department --output dept_headcount.png
```

**Average salary by department:**
```bash
python visualize.py employees.csv --type bar --x department --y salary --output avg_salary.png
```

**Sales over time:**
```bash
python visualize.py sales.csv --type line --x month --y revenue --output revenue_trend.png
```

---

## Common Patterns

### Complete Analysis Workflow

```bash
# 1. Explore data structure
python extract.py data.csv --format table | head -20

# 2. Get statistics
python stats.py data.csv --correlations

# 3. Create visualizations
python visualize.py data.csv --type histogram --x age --output age_dist.png
python visualize.py data.csv --type scatter --x age --y salary --output age_salary.png

# 4. Filter and export insights
python extract.py data.csv --filter "salary > 100000" --output high_earners.csv
python stats.py high_earners.csv
```

### Data Quality Check

```bash
# Check for missing values and data types
python stats.py data.csv --no-info

# Visualize distributions to spot outliers
python visualize.py data.csv --type histogram --x salary --output salary_dist.png
```

### Comparative Analysis

```bash
# Extract subsets
python extract.py data.csv --filter "department == 'Engineering'" --output eng.csv
python extract.py data.csv --filter "department == 'Sales'" --output sales.csv

# Compare statistics
python stats.py eng.csv --no-info
python stats.py sales.csv --no-info

# Visualize comparison
python visualize.py data.csv --type bar --x department --y salary --output dept_comparison.png
```

---

## Troubleshooting

### Common Issues

**Issue: "pandas is not installed"**
```bash
# Solution:
pip install pandas matplotlib seaborn numpy
```

**Issue: "Column not found"**
```bash
# Check available columns:
python extract.py data.csv --format table | head -5

# Or use wildcard:
python extract.py data.csv --columns "*" --format table
```

**Issue: "No numeric columns found"**
```bash
# Check data types:
python stats.py data.csv

# Convert columns if needed:
python extract.py data.csv --columns age,salary --output numeric_only.csv
python stats.py numeric_only.csv
```

**Issue: "Invalid filter expression"**
```bash
# Common mistakes:
# ❌ --filter "age = 30"        (use == not =)
# ❌ --filter "name = John"     (missing quotes)
# ✅ --filter "age == 30"
# ✅ --filter "name == 'John'"
```

**Issue: Chart not displaying**
```bash
# Charts are saved to files, not displayed
# Check the output file:
ls -lh chart.png

# Specify custom output path:
python visualize.py data.csv --type histogram --x age --output /path/to/output.png
```

### Performance Tips

**Large files (>100MB):**
```bash
# Filter early to reduce memory usage
python extract.py large_file.csv --filter "date > '2024-01-01'" --output recent.csv
python stats.py recent.csv
```

**Many columns:**
```bash
# Select only needed columns
python extract.py data.csv --columns id,date,value --output subset.csv
```

**Slow visualizations:**
```bash
# Sample data first
python extract.py data.csv --filter "random() < 0.1" --output sample.csv
python visualize.py sample.csv --type scatter --x age --y salary
```

### Data Format Requirements

**CSV:**
- First row must be column headers
- Consistent delimiter (comma)
- UTF-8 encoding recommended

**JSON:**
- Array of objects: `[{"col1": val1}, {"col2": val2}]`
- Or object with arrays: `{"col1": [val1, val2], "col2": [val3, val4]}`

**TSV:**
- Tab-separated values
- Use `.tsv` extension

---

## Advanced Usage

### Chaining Operations

```bash
# Extract → Filter → Analyze → Visualize
python extract.py raw_data.csv \
  --columns date,product,revenue,units \
  --filter "date >= '2024-01-01' and revenue > 0" \
  --output clean_data.csv

python stats.py clean_data.csv --correlations

python visualize.py clean_data.csv \
  --type line --x date --y revenue \
  --output revenue_trend.png
```

### Batch Processing

```bash
# Analyze multiple files
for file in data/*.csv; do
  echo "Processing $file"
  python stats.py "$file" --no-info > "${file%.csv}_stats.txt"
done
```

### Custom Workflows

```bash
# Department-specific analysis
for dept in Engineering Sales Marketing; do
  python extract.py employees.csv \
    --filter "department == '$dept'" \
    --output "${dept}_employees.csv"
  
  python stats.py "${dept}_employees.csv" > "${dept}_stats.txt"
  
  python visualize.py "${dept}_employees.csv" \
    --type histogram --x salary \
    --output "${dept}_salary_dist.png"
done
```
