import ibis

def read_csv_to_ibis(file_path: str) -> ibis.expr.types.TableExpr:
    """Read a CSV file into an Ibis table expression.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        Ibis table expression representing the CSV data
        
    Raises:
        FileNotFoundError: If specified file doesn't exist
    """
    try:
        return ibis.read_csv(file_path)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"CSV file not found at {file_path}") from e
