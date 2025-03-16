```python
from __future__ import annotations

from collections.abc import Sequence
from string import ascii_letters, digits, hexdigits
from urllib.parse import quote as encode_uri_component

ASCII_LETTERS_AND_DIGITS = ascii_letters + digits
ENCODE_DEFAULT_CHARS = ";/?:@&=+$,-_.!~*'()#"
ENCODE_COMPONENT_CHARS = "-_.!~*'()"

encode_cache: dict[str, list[str]] = {}


def _get_encode_cache(exclude: str) -> Sequence[str]:
    """Create a lookup array for percent-encoding.

    Anything but characters in `chars` string and alphanumeric chars is
    percent-encoded.

    Args:
        exclude: List of characters to exclude from encoding.

    Returns:
        A sequence of strings representing the encoding cache.
    """
    if exclude in encode_cache:
        return encode_cache[exclude]

    cache: list[str] = []
    encode_cache[exclude] = cache

    for i in range(128):
        ch = chr(i)

        if ch in ASCII_LETTERS_AND_DIGITS:
            # always allow unencoded alphanumeric characters
            cache.append(ch)
        else:
            cache.append("%" + ("0" + hex(i)[2:].upper())[-2:])

    for i in range(len(exclude)):
        cache[ord(exclude[i])] = exclude[i]

    return cache


def encode(
    string: str, exclude: str = ENCODE_DEFAULT_CHARS, *, keep_escaped: bool = True
) -> str:
    """Encode unsafe characters with percent-encoding.

    Skips already encoded sequences.

    Args:
        string: String to encode.
        exclude: List of characters to ignore (in addition to a-zA-Z0-9).
        keep_escaped: Don't encode '%' in a correct escape sequence.

    Returns:
        The encoded string.
    """
    result = ""

    cache = _get_encode_cache(exclude)

    string_length = len(string)
    i = 0
    while i < string_length:
        code = ord(string[i])

        # %
        if keep_escaped and code == 0x25 and i + 2 < string_length:
            if all(c in hexdigits for c in string[i + 1 : i + 3]):
                result += string[i : i + 3]
                i += 3
                continue

        if code < 128:
            result += cache[code]
            i += 1
            continue

        if 0xD800 <= code <= 0xDFFF:
            if 0xD800 <= code <= 0xDBFF and i + 1 < string_length:
                next_code = ord(string[i + 1])
                if 0xDC00 <= next_code <= 0xDFFF:
                    result += encode_uri_component(string[i] + string[i + 1])
                    i += 2
                    continue
            result += "%EF%BF%BD"
            i += 1
            continue

        result += encode_uri_component(string[i])
        i += 1

    return result
```
