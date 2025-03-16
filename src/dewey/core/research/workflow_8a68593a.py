```python
"""Workflow package for research operations."""

from typing import List, Tuple


def calculate_average(numbers: List[float]) -> float:
    """Calculates the average of a list of numbers.

    Args:
        numbers: A list of numbers to calculate the average from.

    Returns:
        The average of the numbers in the input list.
        Returns 0.0 if the list is empty.
    """
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


def find_max_min(numbers: List[float]) -> Tuple[float, float]:
    """Finds the maximum and minimum values in a list of numbers.

    Args:
        numbers: A list of numbers to find the maximum and minimum from.

    Returns:
        A tuple containing the maximum and minimum values in the list.
        Returns (0.0, 0.0) if the list is empty.
    """
    if not numbers:
        return 0.0, 0.0
    return max(numbers), min(numbers)


def process_data(data: List[float]) -> Tuple[float, float, float]:
    """Processes a list of data to calculate average, max, and min.

    Args:
        data: A list of numerical data.

    Returns:
        A tuple containing the average, maximum, and minimum values
        from the input data.
    """
    average = calculate_average(data)
    maximum, minimum = find_max_min(data)
    return average, maximum, minimum


if __name__ == '__main__':
    sample_data = [1.0, 2.0, 3.0, 4.0, 5.0]
    avg, max_val, min_val = process_data(sample_data)

    print(f"Data: {sample_data}")
    print(f"Average: {avg}")
    print(f"Maximum: {max_val}")
    print(f"Minimum: {min_val}")
```
