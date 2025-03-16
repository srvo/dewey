```python
from typing import List, Union, Tuple, Optional


def processData(data: List[Union[int, float, str]], 
                  *,
                  multiplier: float = 1.0,
                  ignore_errors: bool = False,
                  default_value: Optional[float] = None) -> List[float]:
    """Processes a list of mixed-type data, converting numeric values to floats,
    applying a multiplier, and handling potential errors.

    This function iterates through a list of data, attempting to convert each element
    to a float.  If the element is already a float or an integer, it's converted directly.
    If the element is a string, it attempts to convert it to a float.  Any other data type
    will raise a TypeError unless `ignore_errors` is set to True.

    The function then applies a multiplier to each converted float.  If a conversion
    error occurs and `ignore_errors` is True, the `default_value` is used. If
    `default_value` is None, a ValueError is raised.

    Args:
        data: A list of mixed-type data (int, float, str).
        multiplier: A float multiplier to apply to each converted value. Defaults to 1.0.
        ignore_errors: A boolean indicating whether to ignore conversion errors.
                       If True, errors are handled by using `default_value`.
                       Defaults to False.
        default_value: An optional float value to use when conversion errors are ignored.
                       If None and `ignore_errors` is True, a ValueError is raised.
                       Defaults to None.

    Returns:
        A list of floats, where each element is the result of converting and multiplying
        the corresponding element in the input data.

    Raises:
        TypeError: If an element in the input data is not an int, float, or string,
                   and `ignore_errors` is False.
        ValueError: If a string cannot be converted to a float, and `ignore_errors` is False.
        ValueError: If a conversion error occurs, `ignore_errors` is True, and
                    `default_value` is None.

    Examples:
        >>> process_data([1, 2.5, "3"])
        [1.0, 2.5, 3.0]

        >>> process_data([1, 2.5, "3"], multiplier=2.0)
        [2.0, 5.0, 6.0]

        >>> process_data([1, "abc", 3], ignore_errors=True, default_value=0.0)
        [1.0, 0.0, 3.0]

        >>> process_data([1, "abc", 3])
        Traceback (most recent call last):
          ...
        ValueError: could not convert string to float: 'abc'

        >>> process_data([1, [1,2], 3])
        Traceback (most recent call last):
          ...
        TypeError: Unsupported data type: <class 'list'>

        >>> process_data([1, "abc", 3], ignore_errors=True)
        Traceback (most recent call last):
          ...
        ValueError: default_value must be provided when ignore_errors is True
    """

    result: List[float] = []
    for item in data:
        try:
            if isinstance(item, (int, float)):
                value = float(item)
            elif isinstance(item, str):
                value = float(item)
            else:
                raise TypeError(f"Unsupported data type: {type(item)}")
            result.append(value * multiplier)
        except ValueError as e:
            if ignore_errors:
                if default_value is None:
                    raise ValueError("default_value must be provided when ignore_errors is True") from e
                result.append(default_value)
            else:
                raise
        except TypeError as e:
            if ignore_errors:
                if default_value is None:
                    raise ValueError("default_value must be provided when ignore_errors is True") from e
                result.append(default_value)
            else:
                raise

    return result
```
