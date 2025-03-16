```python
import argparse
import csv
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

TYPE_PRIORITY: List[str] = [
    'null',
    'boolean',
    'integer',
    'float',
    'percentage',
    'datetime',
    'string',
]


def infer_schema(
    file_path: str, sample_size: int = 1000
) -> Dict[str, Dict[str, Any]]:
    """Infer schema from CSV file by analyzing column values.

    Args:
        file_path: Path to CSV file to analyze.
        sample_size: Number of rows to sample for type detection.

    Returns:
        Dictionary mapping column names to their inferred schema properties.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        schema: Dict[str, defaultdict] = {
            col: defaultdict(int) for col in columns
        }

        for i, row in enumerate(reader):
            if i >= sample_size:
                break

            for col in columns:
                value = row[col].strip()

                _analyze_value(value, col, schema)

    # Determine final types
    final_schema = {}
    for col, counts in schema.items():
        inferred_type = _determine_inferred_type(counts)

        final_schema[col] = {
            'type': inferred_type,
            'max_length': counts.get('max_length'),
            'null_count': counts.get('null_count', 0),
            'format': counts.get('format'),
        }

    return final_schema


def _analyze_value(
    value: str, col: str, schema: Dict[str, defaultdict]
) -> None:
    """Analyzes a single value and updates the schema accordingly."""
    # Detect value type
    if not value:
        schema[col]['null_count'] += 1
        return

    # Check for zero-padded numbers
    is_zero_padded = len(value) > 1 and value[0] == '0' and value.isdigit()
    if is_zero_padded:
        schema[col]['zero_padded'] = True

    # Check for percentages
    contains_percentage = value.endswith('%')
    if contains_percentage:
        schema[col]['contains_percentage'] = True
        value = value.replace('%', '')  # Remove % for type checking

    # Detect type
    if _is_boolean(value):
        schema[col]['booleans'] += 1
    elif _is_integer(value):
        schema[col]['integers'] += 1
    elif _is_float(value):
        schema[col]['floats'] += 1
    elif datetime_format := _is_datetime(value):
        schema[col]['datetimes'] += 1
        schema[col]['format'] = datetime_format
    else:
        schema[col]['strings'] += 1
        schema[col]['max_length'] = max(
            schema[col].get('max_length', 0), len(value)
        )


def _determine_inferred_type(counts: defaultdict) -> str:
    """Determines the inferred type based on the counts."""
    types_present = [
        t for t in TYPE_PRIORITY if counts.get(f'{t}s', 0) > 0
    ]
    inferred_type = 'string'  # default

    if 'contains_percentage' in counts:
        inferred_type = 'percentage'
    elif 'zero_padded' in counts:
        inferred_type = 'string'
    elif types_present:
        for t in reversed(TYPE_PRIORITY):
            if t in types_present:
                inferred_type = t
                break
    return inferred_type


def _is_boolean(value: str) -> bool:
    """Checks if a value is boolean."""
    return value.lower() in ('true', 'false', 't', 'f')


def _is_integer(value: str) -> bool:
    """Checks if a value is an integer."""
    try:
        int(value)
        return True
    except ValueError:
        return False


def _is_float(value: str) -> bool:
    """Checks if a value is a float."""
    try:
        float(value)
        return True
    except ValueError:
        return False


def _is_datetime(value: str) -> Optional[str]:
    """Checks if a value is a datetime and returns the format."""
    formats = [
        ('%Y-%m-%d', 'date'),
        ('%Y-%m-%d %H:%M:%S', 'datetime'),
        ('%Y-%m-%dT%H:%M:%S', 'iso8601'),
        ('%m/%d/%Y %I:%M %p', 'datetime'),
        ('%d-%b-%Y', 'date'),  # 01-Jan-2023
        ('%Y%m%d', 'compact_date'),  # 20230101
        ('%H:%M:%S', 'time'),
    ]

    for fmt, fmt_name in formats:
        try:
            datetime.strptime(value, fmt)
            return fmt_name
        except ValueError:
            continue
    return None


def _format_schema_output(schema: Dict[str, Dict[str, Any]]) -> str:
    """Formats the schema output for printing."""
    output = []
    for col, meta in schema.items():
        type_info = meta['type'].upper()
        details = []

        if type_info == 'DATETIME':
            if fmt := meta.get('format'):
                details.append(f"format: {fmt}")
        elif type_info == 'PERCENTAGE':
            if meta.get('contains_percentage'):
                details.append("contains percentages")
        elif type_info == 'STRING':
            if meta['max_length']:
                details.append(f"max_length: {meta['max_length']}")
            if meta.get('zero_padded'):
                details.append("zero-padded numbers detected")

        details.append(f"null values: {meta['null_count']}")

        output.append(f"▪ {col}")
        output.append(f"  Type: {type_info}")
        output.append("\n".join([f"  - {d}" for d in details]))

    return "\n".join(output)


def main() -> None:
    """Main function to parse arguments and print the schema."""
    parser = argparse.ArgumentParser(description='Infer schema from CSV file')
    parser.add_argument(
        '--file', type=str, required=True, help='Path to CSV file'
    )
    parser.add_argument(
        '--sample',
        type=int,
        default=1000,
        help='Number of rows to sample for analysis',
    )
    args = parser.parse_args()

    schema = infer_schema(args.file, args.sample)
    print(_format_schema_output(schema))


if __name__ == '__main__':
    main()
```
