```python
from __future__ import annotations

from collections.abc import Sequence
import functools
import re

DECODE_DEFAULT_CHARS: str = ";/?:@&=+$,#"
DECODE_COMPONENT_CHARS: str = ""

decode_cache: dict[str, list[str]] = {}


def _get_decode_cache(exclude: str) -> Sequence[str]:
    """Retrieves or creates a decoding cache for the given excluded characters.

    Args:
        exclude: A string containing characters to exclude from decoding.

    Returns:
        A sequence of strings representing the decoding cache.
    """
    if exclude in decode_cache:
        return decode_cache[exclude]

    cache: list[str] = []
    decode_cache[exclude] = cache

    for i in range(128):
        ch = chr(i)
        cache.append(ch)

    for i in range(len(exclude)):
        ch_code = ord(exclude[i])
        cache[ch_code] = "%" + ("0" + hex(ch_code)[2:].upper())[-2:]

    return cache


def _repl_func_with_cache(match: re.Match, cache: Sequence[str]) -> str:
    """Replaces percent-encoded sequences using a provided cache.

    Args:
        match: A regex match object containing the percent-encoded sequence.
        cache: A sequence of strings representing the decoding cache.

    Returns:
        The decoded string.
    """
    seq = match.group()
    result = ""

    i = 0
    l = len(seq)
    while i < l:
        b1 = int(seq[i + 1 : i + 3], 16)

        if b1 < 0x80:
            result += cache[b1]
            i += 3
            continue

        if (b1 & 0xE0) == 0xC0 and (i + 3 < l):
            # 110xxxxx 10xxxxxx
            b2 = int(seq[i + 4 : i + 6], 16)

            if (b2 & 0xC0) == 0x80:
                all_bytes = bytes((b1, b2))
                try:
                    result += all_bytes.decode()
                except UnicodeDecodeError:
                    result += "\ufffd" * 2

                i += 6
                continue

        if (b1 & 0xF0) == 0xE0 and (i + 6 < l):
            # 1110xxxx 10xxxxxx 10xxxxxx
            b2 = int(seq[i + 4 : i + 6], 16)
            b3 = int(seq[i + 7 : i + 9], 16)

            if (b2 & 0xC0) == 0x80 and (b3 & 0xC0) == 0x80:
                all_bytes = bytes((b1, b2, b3))
                try:
                    result += all_bytes.decode()
                except UnicodeDecodeError:
                    result += "\ufffd" * 3

                i += 9
                continue

        if (b1 & 0xF8) == 0xF0 and (i + 9 < l):
            # 111110xx 10xxxxxx 10xxxxxx 10xxxxxx
            b2 = int(seq[i + 4 : i + 6], 16)
            b3 = int(seq[i + 7 : i + 9], 16)
            b4 = int(seq[i + 10 : i + 12], 16)

            if (b2 & 0xC0) == 0x80 and (b3 & 0xC0) == 0x80 and (b4 & 0xC0) == 0x80:
                all_bytes = bytes((b1, b2, b3, b4))
                try:
                    result += all_bytes.decode()
                except UnicodeDecodeError:
                    result += "\ufffd" * 4

                i += 12
                continue

        result += "\ufffd"
        i += 3

    return result


def decode(string: str, exclude: str = DECODE_DEFAULT_CHARS) -> str:
    """Decodes a percent-encoded string.

    Args:
        string: The string to decode.
        exclude: A string containing characters to exclude from decoding.
            Defaults to DECODE_DEFAULT_CHARS.

    Returns:
        The decoded string.
    """
    cache = _get_decode_cache(exclude)
    repl_func = functools.partial(_repl_func_with_cache, cache=cache)
    return re.sub(r"(%[a-f0-9]{2})+", repl_func, string, flags=re.IGNORECASE)
```
