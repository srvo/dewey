```python
import pandas as pd
import ibis
import ibis.expr.datatypes as dt
from pathlib import Path
from typing import Optional, List, Dict, Union, Any
from ibis.backends.base import BaseBackend

def read_csv_to_ibis(
    file_path: Union[str, Path],
    client: Optional[BaseBackend] = None,
    schema: Optional[Dict[str, str]] = None,
    delimiter: str = ",",
    header: bool = True,
    usecols: Optional[List[str]] = None,
    skiprows: Optional[int] = None,
    nrows: Optional[int] = None,
    dtype: Optional[Dict[str, str]] = None,
    index_col: Optional[Union[str, int, List[Union[str, int]]]] = None,
) -> ibis.Expr:
    """Reads a CSV file into an Ibis expression.

    Args:
        file_path: The path to the CSV file.
        client: Optional Ibis client to use. If None, a default client is created.
        schema: Optional dictionary specifying the schema of the CSV file.
            Keys are column names, and values are Ibis data types (e.g., "int64", "float64", "string").
            If None, the schema is inferred from the CSV file.
        delimiter: The delimiter used in the CSV file. Defaults to ",".
        header: Whether the CSV file has a header row. Defaults to True.
        usecols: Optional list of column names to read from the CSV file.
            If None, all columns are read.
        skiprows: Optional number of rows to skip at the beginning of the CSV file.
        nrows: Optional number of rows to read from the CSV file.
        dtype: Optional dictionary specifying the data types of the columns.
            Keys are column names, and values are Pandas data types (e.g., "int64", "float64", "object").
            This is used by Pandas `read_csv` function.
        index_col: Optional column name(s) to use as the index. Can be a single column name,
            a column index, or a list of column names or indices.

    Returns:
        An Ibis expression representing the data in the CSV file.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the schema is invalid or if there is an error during CSV parsing.

    Examples:
        Read a CSV file into an Ibis expression:

        >>> import ibis
        >>> from pathlib import Path
        >>> file_path = Path("data.csv") # Create a dummy data.csv
        >>> with open(file_path, "w") as f:
        ...     f.write("col1,col2\\n1,2\\n3,4")
        >>> expr = read_csv_to_ibis(file_path)
        >>> expr.execute() # doctest: +SKIP

        Read a CSV file with a specified schema:

        >>> schema = {"col1": "int64", "col2": "int64"}
        >>> expr = read_csv_to_ibis(file_path, schema=schema)
        >>> expr.execute() # doctest: +SKIP

        Read a CSV file with a different delimiter:

        >>> file_path = Path("data.csv") # Create a dummy data.csv
        >>> with open(file_path, "w") as f:
        ...     f.write("col1;col2\\n1;2\\n3;4")
        >>> expr = read_csv_to_ibis(file_path, delimiter=";")
        >>> expr.execute() # doctest: +SKIP

        Read a CSV file with specific columns:

        >>> expr = read_csv_to_ibis(file_path, usecols=["col1"])
        >>> expr.execute() # doctest: +SKIP

        Read a CSV file with skiprows and nrows:

        >>> file_path = Path("data.csv") # Create a dummy data.csv
        >>> with open(file_path, "w") as f:
        ...     f.write("header1,header2\\nskip1,skip2\\n1,2\\n3,4")
        >>> expr = read_csv_to_ibis(file_path, skiprows=1, nrows=2)
        >>> expr.execute() # doctest: +SKIP
    """
    file_path = Path(file_path) if isinstance(file_path, str) else file_path

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        df = pd.read_csv(
            file_path,
            sep=delimiter,
            header=0 if header else None,
            usecols=usecols,
            skiprows=skiprows,
            nrows=nrows,
            dtype=dtype,
            index_col=index_col,
        )
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {e}")

    if schema:
        try:
            ibis_schema = ibis.schema(
                {col: getattr(dt, dtype)() for col, dtype in schema.items()}
            )
        except AttributeError as e:
            raise ValueError(f"Invalid schema: {e}.  Ensure schema datatypes are valid Ibis datatypes (e.g. 'int64', 'string')")
        
        # Check if schema matches DataFrame columns
        if set(schema.keys()) != set(df.columns):
            raise ValueError("Schema column names do not match DataFrame column names.")

        table = ibis.memtable(df, schema=ibis_schema)

    else:
        table = ibis.memtable(df)

    if client:
        return client.table(table.name)  # Assuming memtable name is accessible
    else:
        return table
```