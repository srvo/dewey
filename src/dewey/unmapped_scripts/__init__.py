```python
def calculate_sum_and_product(numbers: list[float]) -> tuple[float, float]:
    """Calculates the sum and product of a list of numbers.

    Args:
        numbers: A list of numbers (float).

    Returns:
        A tuple containing the sum and product of the numbers.
    """
    if not numbers:
        return 0.0, 1.0

    sum_result = calculate_sum(numbers)
    product_result = calculate_product(numbers)

    return sum_result, product_result


def calculate_sum(numbers: list[float]) -> float:
    """Calculates the sum of a list of numbers.

    Args:
        numbers: A list of numbers (float).

    Returns:
        The sum of the numbers.
    """
    return sum(numbers)


def calculate_product(numbers: list[float]) -> float:
    """Calculates the product of a list of numbers.

    Args:
        numbers: A list of numbers (float).

    Returns:
        The product of the numbers.
    """
    product = 1.0
    for number in numbers:
        product *= number
    return product
```
