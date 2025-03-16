```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mdurl._url import URL


def _format_authority(url: URL) -> str:
    """Formats the authority part of the URL (auth, hostname, port).

    Args:
        url: The URL object.

    Returns:
        The formatted authority string.
    """
    authority = ""
    if url.auth:
        authority += url.auth + "@"

    if url.hostname:
        if ":" in url.hostname:
            # ipv6 address
            authority += "[" + url.hostname + "]"
        else:
            authority += url.hostname

    if url.port:
        authority += ":" + url.port

    return authority


def format_url(url: URL) -> str:  # noqa: A001
    """Formats a URL object into a string.

    Args:
        url: The URL object to format.

    Returns:
        The formatted URL string.
    """
    result = ""

    result += url.protocol or ""
    if url.slashes:
        result += "//"

    result += _format_authority(url)

    result += url.pathname or ""
    result += url.search or ""
    result += url.hash or ""

    return result
```
