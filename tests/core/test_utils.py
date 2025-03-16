import pytest

from dewey.utils import read_csv_to_ibis


def test_read_csv_to_ibis_success(tmp_path) -> None:
    """Test successful CSV reading with Ibis."""
    test_csv = tmp_path / "test.csv"
    test_csv.write_text("name,age\nAlice,30\nBob,25")

    table = read_csv_to_ibis(str(test_csv))
    assert table.count().execute() == 2
    assert "name" in table.columns
    assert "age" in table.columns


def test_read_csv_to_ibis_missing_file() -> None:
    """Test FileNotFoundError for missing CSV."""
    with pytest.raises(FileNotFoundError):
        read_csv_to_ibis("non_existent.csv")
