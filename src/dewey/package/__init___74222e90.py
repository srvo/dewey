"""Package initialization file."""


def add(x, y):
    """Adds two numbers.

    Args:
    ----
        x: The first number.
        y: The second number.

    Returns:
    -------
        The sum of x and y.

    """
    return x + y


def subtract(x, y):
    """Subtracts two numbers.

    Args:
    ----
        x: The first number.
        y: The second number.

    Returns:
    -------
        The difference of x and y.

    """
    return x - y


def multiply(x: float, y: float) -> float:
    """Multiplies two numbers.

    Args:
    ----
        x: The first number.
        y: The second number.

    Returns:
    -------
        The product of x and y.

    """
    return x * y


def divide(x: float, y: float) -> float:
    """Divides two numbers.

    Args:
    ----
        x: The first number.
        y: The second number.

    Returns:
    -------
        The quotient of x and y.

    """
    return x / y
