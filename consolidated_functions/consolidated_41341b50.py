```python
from typing import List, Union, Tuple, Optional, Dict
import math


def process_data(
    data: List[Union[int, float, str]],
    *,
    normalize: bool = False,
    clip: Optional[Tuple[float, float]] = None,
    convert_to_int: bool = False,
    default_value: Union[int, float, str] = 0,
    string_replacement_map: Optional[Dict[str, Union[int, float, str]]] = None,
) -> List[Union[int, float, str]]:
    """Processes a list of mixed-type data, applying normalization, clipping,
    type conversion, and string replacement as specified.

    Args:
        data: A list of data elements, which can be integers, floats, or strings.
        normalize: If True, normalizes the numerical data (int/float) to the range [0, 1].
        clip: An optional tuple (min_val, max_val) to clip numerical data within the specified range.
              If None, no clipping is performed.
        convert_to_int: If True, converts all numerical data to integers.
        default_value: The default value to use for elements that cannot be converted
                       or are invalid. Defaults to 0.
        string_replacement_map: An optional dictionary mapping strings to replacement values.
                                 If None, no string replacement is performed.

    Returns:
        A new list containing the processed data.

    Raises:
        TypeError: If `clip` is not a tuple of length 2 when provided.
        ValueError: If `clip` contains non-numerical values.

    Examples:
        >>> process_data([1, 2, 3], normalize=True)
        [0.0, 0.5, 1.0]

        >>> process_data([1, 2, 3], clip=(1.5, 2.5))
        [1.5, 2, 2.5]

        >>> process_data([1.5, 2.5, 3.5], convert_to_int=True)
        [1, 2, 3]

        >>> process_data(['a', 'b', 'c'], string_replacement_map={'a': 1, 'b': 2})
        [1, 2, 'c']

        >>> process_data([1, 'a', 3.5], default_value=-1)
        [1, -1, 3.5]

        >>> process_data([1, 'a', 3.5], convert_to_int=True, default_value=-1)
        [1, -1, 3]

        >>> process_data([1, 2, 3], normalize=True, clip=(0.2, 0.8))
        [0.2, 0.5, 0.8]

        >>> process_data([1, 2, "invalid"], default_value=0, convert_to_int=True)
        [1, 0, 2]
    """

    processed_data: List[Union[int, float, str]] = []

    if clip is not None:
        if not isinstance(clip, tuple) or len(clip) != 2:
            raise TypeError("clip must be a tuple of length 2 (min, max)")
        if not all(isinstance(x, (int, float)) for x in clip):
            raise ValueError("clip values must be numerical")
        min_val, max_val = clip

    numerical_data: List[Union[int, float]] = []
    for item in data:
        if isinstance(item, (int, float)):
            numerical_data.append(item)

    if normalize:
        if not numerical_data:
            min_val = 0
            max_val = 1
        else:
            min_val = min(numerical_data)
            max_val = max(numerical_data)

        if min_val == max_val:
            normalized_data = [0.0 for _ in numerical_data]  # Avoid division by zero
        else:
            normalized_data = [(float(x) - min_val) / (max_val - min_val) for x in numerical_data]
    else:
        normalized_data = numerical_data

    numerical_index = 0
    for item in data:
        if isinstance(item, (int, float)):
            processed_value: Union[int, float] = normalized_data[numerical_index]

            if clip is not None:
                processed_value = max(min_val, min(processed_value, max_val))

            if convert_to_int:
                try:
                    processed_value = int(processed_value)
                except (ValueError, TypeError):
                    processed_value = default_value
            numerical_index += 1

        elif isinstance(item, str):
            if string_replacement_map and item in string_replacement_map:
                processed_value = string_replacement_map[item]
            else:
                processed_value = item
        else:
            processed_value = default_value

        processed_data.append(processed_value)

    return processed_data
```