---
name: csv-data-validator
description: Validate a CSV file against a JSON schema — checks column types, required fields, ranges, and referential integrity, then produces a validation report.
---

# CSV Data Validator

Validate a CSV data file against a declared schema and report every problem
found, with row and column references.

## Step 1: Schema Discovery and Scoring

Given a schema file and a CSV file, determine how well the CSV's header row
matches the schema's declared columns before running full validation.

```python
def score_schema_match(csv_header, schema_columns):
    matched = [c for c in csv_header if c in schema_columns]
    missing = [c for c in schema_columns if c not in csv_header]
    extra = [c for c in csv_header if c not in schema_columns]
    score = len(matched) / max(len(schema_columns), 1)
    return {
        "score": score,
        "matched": matched,
        "missing": missing,
        "extra": extra,
    }
```

If the score is below 0.5, stop and report the mismatch to the user before
continuing — do not attempt to validate a CSV that does not resemble the
schema.

## Step 2: Type Validation

For every declared column, check that every cell in that column parses as
the declared type (`string`, `integer`, `float`, `date`, `email`, `phone`,
`boolean`).

```python
import re

TYPE_CHECKS = {
    "integer": lambda v: re.fullmatch(r"-?\d+", v) is not None,
    "float": lambda v: re.fullmatch(r"-?\d+(\.\d+)?", v) is not None,
    "date": lambda v: re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) is not None,
    "email": lambda v: re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v) is not None,
    "phone": lambda v: re.fullmatch(r"\+?\d[\d\-\s]{6,}\d", v) is not None,
    "boolean": lambda v: v.lower() in {"true", "false", "1", "0"},
    "string": lambda v: True,
}

def validate_type(value, declared_type):
    check = TYPE_CHECKS.get(declared_type)
    if check is None:
        raise ValueError(f"Unknown type: {declared_type}")
    return check(value)
```

## Step 3: Required-Field Validation

For every column marked `"required": true` in the schema, check that no row
has a blank or missing value in that column.

```python
def validate_required(rows, column, is_required):
    if not is_required:
        return []
    violations = []
    for i, row in enumerate(rows):
        value = row.get(column, "")
        if value is None or str(value).strip() == "":
            violations.append(i)
    return violations
```

## Step 4: Range Validation

For every column with `"min"` and/or `"max"` declared, check that every
numeric value falls within the declared bounds.

```python
def validate_range(rows, column, min_value=None, max_value=None):
    violations = []
    for i, row in enumerate(rows):
        raw = row.get(column)
        if raw is None or raw == "":
            continue
        value = float(raw)
        if min_value is not None and value < min_value:
            violations.append((i, value, "below-min"))
        if max_value is not None and value > max_value:
            violations.append((i, value, "above-max"))
    return violations
```

## Step 5: Referential Integrity

For every column with a `"references"` block, check that every value in
that column exists as a value in the referenced file's referenced column.

```python
def validate_references(rows, column, ref_file, ref_column, ref_loader):
    ref_values = set(ref_loader(ref_file, ref_column))
    violations = []
    for i, row in enumerate(rows):
        value = row.get(column)
        if value is None or value == "":
            continue
        if value not in ref_values:
            violations.append((i, value))
    return violations
```

## Step 6: Report Generation

Combine the results of Steps 2–5 into a single structured report, grouped by
row, sorted by row number, with a summary count at the top.

```python
def build_report(type_errors, required_errors, range_errors, ref_errors):
    by_row = {}
    for row_idx, col, kind in type_errors:
        by_row.setdefault(row_idx, []).append(f"{col}: type mismatch ({kind})")
    for row_idx in required_errors:
        by_row.setdefault(row_idx, []).append("required field missing")
    for row_idx, value, kind in range_errors:
        by_row.setdefault(row_idx, []).append(f"range violation ({kind}): {value}")
    for row_idx, value in ref_errors:
        by_row.setdefault(row_idx, []).append(f"referential integrity: {value} not found")

    report_lines = [f"Total rows with errors: {len(by_row)}"]
    for row_idx in sorted(by_row):
        report_lines.append(f"Row {row_idx}: " + "; ".join(by_row[row_idx]))
    return "\n".join(report_lines)
```

## Schema Format

Schemas are JSON files with the following shape:

```json
{
  "name": "...",
  "description": "...",
  "columns": {
    "<col>": {
      "type": "string|integer|float|date|email|phone|boolean",
      "required": true,
      "min": 0,
      "max": 100,
      "references": { "file": "path.csv", "column": "id" }
    }
  }
}
```

## Common Issues

- **Encoding mismatches**: CSVs exported from spreadsheet tools sometimes
  use a BOM or non-UTF-8 encoding. If parsing fails outright, ask the user
  which encoding the file was exported with before proceeding.
- **Ambiguous date formats**: `01/02/2024` could be January 2nd or February
  1st depending on locale. When a schema's `date` column doesn't specify a
  format, ask the user to confirm rather than guessing.
- **Schema drift**: if the CSV header has columns the schema doesn't
  mention, decide with the user whether those are safe to ignore or signal
  that the schema itself is out of date.
