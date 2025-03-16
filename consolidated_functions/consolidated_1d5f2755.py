```python
from typing import Any, Optional, Union

def default(obj: Any, default_value: Any = None) -> Any:
    """
    Returns the object if it's not None, otherwise returns a default value.

    This function provides a concise way to handle potential None values and
    provide a fallback. It's similar to the null-coalescing operator in some
    other languages.

    Args:
        obj: The object to check for None.  Can be any type.
        default_value: The value to return if `obj` is None. Defaults to None.

    Returns:
        The original object (`obj`) if it's not None, otherwise the
        `default_value`.

    Examples:
        >>> default(5)
        5
        >>> default(None, 10)
        10
        >>> default(None)
        None
        >>> default("", "default_string")
        ''
    """
    if obj is not None:
        return obj
    else:
        return default_value
```
