from pathlib import Path

import ibis
import pytest

from src.dewey.utils.ibis_utils import readCsvToIbis


def test_read_csv_to_ibis_success(tmp_path: Path) -> None:
    """Test successful CSV reading with Ibis.

    Args:
        tmp_path: pytest fixture for a temporary directory.

    """
    csv_content = "age,age\nAlice,30\nBob,25"
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    table = readCsvToIbis(csv_file, table_name="test_table")
    assert table.column("age").count().execute() == 2
    assert table.count().execute() == 2


def test_read_csv_to_ibis_missing_file() -> None:
    """Test FileNotFoundError for missing CSV."""
    with pytest.raises(FileNotFoundError):
        readCsvToIbis("non_existent.csv")


def test_read_csv_to_ibis_with_schema(tmp_path: Path) -> None:
    """Test reading CSV with a specified schema.

    Args:
        tmp_path: pytest fixture for a temporary directory.

    """
    csv_content = "col1,col2\n1,abc\n2,def"
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    schema = ibis.schema({"col1": "int64", "col2": "string"})
    table = readCsvToIbis(csv_file, table_name="test_table", schema=schema)
    assert table.count().execute() == 2
    assert table.schema() == schema


def test_read_csv_to_ibis_with_delimiter(tmp_path: Path) -> None:
    """Test reading CSV with a custom delimiter.

    Args:
        tmp_path: pytest fixture for a temporary directory.

    """
    csv_content = "col1|col2\n1|abc\n2|def"
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    table = readCsvToIbis(csv_file, table_name="test_table", delimiter="|")
    assert table.count().execute() == 2


def test_read_csv_to_ibis_no_header(tmp_path: Path) -> None:
    """Test reading CSV without a header row.

    Args:
        tmp_path: pytest fixture for a temporary directory.

    """
    csv_content = "1,abc\n2,def"
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    table = readCsvToIbis(csv_file, table_name="test_table", header=False)
    assert table.count().execute() == 2


def test_read_csv_to_ibis_usecols(tmp_path: Path) -> None:
    """Test reading specific columns from a CSV.

    Args:
        tmp_path: pytest fixture for a temporary directory.

    """
    csv_content = "col1,col2,col3\n1,abc,xyz\n2,def,uvw"
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    table = readCsvToIbis(csv_file, table_name="test_table", usecols=["col1", "col3"])
    assert table.count().execute() == 2
    assert set(table.columns) == {"col1", "col3"}


def test_read_csv_to_ibis_skiprows(tmp_path: Path) -> None:
    """Test skipping rows at the beginning of the CSV.

    Args:
        tmp_path: pytest fixture for a temporary directory.

    """
    csv_content = "header1,header2\nskip1,skip2\n1,abc\n2,def"
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    table = readCsvToIbis(csv_file, table_name="test_table", skiprows=2)
    assert table.count().execute() == 2


def test_read_csv_to_ibis_nrows(tmp_path: Path) -> None:
    """Test reading a limited number of rows from the CSV.

    Args:
        tmp_path: pytest fixture for a temporary directory.

    """
    csv_content = "col1,col2\n1,abc\n2,def\n3,ghi"
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    table = readCsvToIbis(csv_file, table_name="test_table", nrows=2)
    assert table.count().execute() == 2


def test_read_csv_to_ibis_dtype(tmp_path: Path) -> None:
    """Test specifying data types for columns.

    Args:
        tmp_path: pytest fixture for a temporary directory.

    """
    csv_content = "col1,col2\n1,abc\n2,def"
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    table = readCsvToIbis(csv_file, table_name="test_table", dtype={"col1": "float64"})
    assert table.count().execute() == 2
    assert table.schema()["col1"].name == "col1"
    assert table.schema()["col1"].dtype == "float64"


def test_read_csv_to_ibis_index_col(tmp_path: Path) -> None:
    """Test specifying index column.

    Args:
        tmp_path: pytest fixture for a temporary directory.

    """
    csv_content = "index,col1,col2\n1,abc,def\n2,ghi,jkl"
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    table = readCsvToIbis(csv_file, table_name="test_table", index_col="index")
    assert table.count().execute() == 2
    # Note: Ibis doesn't directly expose the index column in the same way as Pandas.
    # We can verify the table has the correct columns.
    assert set(table.columns) == {"col1", "col2"}


def test_read_csv_to_ibis_invalid_schema(tmp_path: Path) -> None:
    """Test reading CSV with an invalid schema (mismatched column names).

    Args:
        tmp_path: pytest fixture for a temporary directory.

    """
    csv_content = "col1,col2\n1,abc\n2,def"
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    schema = ibis.schema({"col3": "int64", "col4": "string"})
    with pytest.raises(
        ValueError, match="Schema column names do not match CSV column names."
    ):
        readCsvToIbis(csv_file, table_name="test_table", schema=schema)


def test_read_csv_to_ibis_with_client(tmp_path: Path) -> None:
    """Test reading CSV with a specific Ibis client (e.g., DuckDB).

    Args:
        tmp_path: pytest fixture for a temporary directory.

    """
    try:
        import duckdb
        import ibis.duckdb
    except ImportError:
        pytest.skip("duckdb and ibis-duckdb are required for this test.")

    csv_content = "col1,col2\n1,abc\n2,def"
    csv_file = tmp_path / "test.csv"
    csv_file.write_text(csv_content)

    con = duckdb.connect()
    client = ibis.duckdb.connect(con)

    table = readCsvToIbis(csv_file, table_name="test_table", client=client)
    assert table.count().execute() == 2
    con.close()
