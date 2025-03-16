```python
import ibis
import pandas as pd
from typing import Union, Optional

def read_csv_to_ibis(file_path: str,
                     schema: Optional[Union[ibis.Schema, dict]] = None,
                     delimiter: Optional[str] = ',',
                     header: Optional[bool] = True,
                     names: Optional[list[str]] = None,
                     skiprows: Optional[int] = None,
                     nrows: Optional[int] = None,
                     parse_dates: Optional[Union[bool, list[str]]] = False,
                     dtype: Optional[dict[str, str]] = None,
                     encoding: Optional[str] = 'utf-8') -> ibis.Table:
    """Reads a CSV file into an Ibis table expression.

    This function provides a comprehensive way to read CSV files into an Ibis table,
    handling various options for data parsing, schema definition, and file format.
    It leverages the underlying pandas functionality for CSV parsing and then
    converts the pandas DataFrame to an Ibis table expression.

    Args:
        file_path: Path to the CSV file.
        schema:  An optional Ibis schema or a dictionary defining the column names
            and data types. If None, Ibis will infer the schema from the data.
            If a dictionary is provided, it should map column names (strings) to
            Ibis data types (e.g., 'int64', 'string', 'float64').
        delimiter:  The delimiter used to separate fields in the CSV file. Defaults to ','.
        header:  Whether the CSV file has a header row. Defaults to True.
        names:  An optional list of column names.  If provided, it overrides any
            header row in the CSV file.
        skiprows:  Number of rows to skip at the beginning of the file.
        nrows:  Number of rows to read from the file.  If None, all rows are read.
        parse_dates:  Whether to attempt to parse date columns. Can be a boolean
            (True to parse all date-like columns) or a list of column names to parse.
            Defaults to False.
        dtype:  A dictionary specifying the data types for specific columns.
            Keys are column names, and values are pandas data type strings (e.g.,
            'int64', 'float64', 'object').  This is useful for overriding
            Ibis's schema inference or for specifying types that Ibis might not
            infer correctly.
        encoding:  The encoding of the CSV file. Defaults to 'utf-8'.

    Returns:
        An Ibis table expression representing the CSV data.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If schema is provided as a dictionary but the keys are not strings.
        TypeError: If schema is not a valid type (ibis.Schema or dict).
        Exception:  Any exception raised during pandas DataFrame creation or Ibis
            table creation (e.g., due to incorrect data types, parsing errors, etc.).

    Examples:
        >>> # Read a CSV with a header and infer the schema
        >>> table = read_csv_to_ibis("my_data.csv")

        >>> # Read a CSV with a custom schema
        >>> schema = {'col1': 'int64', 'col2': 'string', 'col3': 'float64'}
        >>> table = read_csv_to_ibis("my_data.csv", schema=schema)

        >>> # Read a CSV with a different delimiter and no header
        >>> table = read_csv_to_ibis("my_data.tsv", delimiter="\t", header=False, names=["col1", "col2"])

        >>> # Read a CSV and parse date columns
        >>> table = read_csv_to_ibis("my_data.csv", parse_dates=True)

        >>> # Read a CSV and skip the first 2 rows
        >>> table = read_csv_to_ibis("my_data.csv", skiprows=2)
    """
    try:
        # Handle schema definition
        if schema is not None:
            if isinstance(schema, dict):
                if not all(isinstance(key, str) for key in schema.keys()):
                    raise ValueError("Keys in the schema dictionary must be strings (column names).")
                # Convert schema dict to pandas dtype dict for pandas read_csv
                pandas_dtype = {col: dtype for col, dtype in schema.items()}
            elif not isinstance(schema, ibis.Schema):
                raise TypeError("Schema must be an ibis.Schema object or a dictionary.")
            else:
                pandas_dtype = None  # Let pandas infer types if schema is an Ibis schema
        else:
            pandas_dtype = None

        # Read the CSV into a pandas DataFrame
        df = pd.read_csv(
            file_path,
            sep=delimiter,
            header=0 if header else None,
            names=names,
            skiprows=skiprows,
            nrows=nrows,
            parse_dates=parse_dates,
            dtype=dtype,
            encoding=encoding,
        )

        # Convert the pandas DataFrame to an Ibis table expression
        if schema is not None and isinstance(schema, ibis.Schema):
            # Use the provided Ibis schema
            table = ibis.pandas.connect({'data': df}).table('data', schema=schema)
        else:
            table = ibis.pandas.connect({'data': df}).table('data')

        return table

    except FileNotFoundError:
        raise FileNotFoundError(f"The specified file '{file_path}' does not exist.")
    except Exception as e:
        raise Exception(f"An error occurred while reading the CSV: {e}")
```