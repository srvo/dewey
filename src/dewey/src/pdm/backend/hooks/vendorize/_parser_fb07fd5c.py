```python
"""Handwritten parser of dependency specifiers.

The docstring for each __parse_* function contains EBNF-inspired grammar representing
the implementation.
"""

from __future__ import annotations

import ast
from typing import NamedTuple, Sequence, Tuple, Union

from ._tokenizer import DEFAULT_RULES, Tokenizer


class Node:
    """Base class for nodes in the parsed tree."""

    def __init__(self, value: str) -> None:
        """Initializes a Node with a value.

        Args:
            value: The string value of the node.
        """
        self.value = value

    def __str__(self) -> str:
        """Returns the string representation of the node."""
        return self.value

    def __repr__(self) -> str:
        """Returns the string representation of the node."""
        return f"<{self.__class__.__name__}('{self}')>"

    def serialize(self) -> str:
        """Serializes the node to a string.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError


class Variable(Node):
    """Represents a variable in the parsed tree."""

    def serialize(self) -> str:
        """Serializes the variable to a string."""
        return str(self)


class Value(Node):
    """Represents a value in the parsed tree."""

    def serialize(self) -> str:
        """Serializes the value to a string."""
        return f'"{self}"'


class Op(Node):
    """Represents an operator in the parsed tree."""

    def serialize(self) -> str:
        """Serializes the operator to a string."""
        return str(self)


MarkerVar = Union[Variable, Value]
MarkerItem = Tuple[MarkerVar, Op, MarkerVar]
MarkerAtom = Union[MarkerItem, Sequence["MarkerAtom"]]
MarkerList = Sequence[Union["MarkerList", MarkerAtom, str]]


class ParsedRequirement(NamedTuple):
    """Represents a parsed requirement."""

    name: str
    url: str
    extras: list[str]
    specifier: str
    marker: MarkerList | None


# --------------------------------------------------------------------------------------
# Recursive descent parser for dependency specifier
# --------------------------------------------------------------------------------------
def parse_requirement(source: str) -> ParsedRequirement:
    """Parses a dependency specifier string.

    Args:
        source: The dependency specifier string to parse.

    Returns:
        A ParsedRequirement object representing the parsed specifier.
    """
    return _parse_requirement(Tokenizer(source, rules=DEFAULT_RULES))


def _parse_requirement(tokenizer: Tokenizer) -> ParsedRequirement:
    """Parses a requirement from a tokenizer.

    requirement = WS? IDENTIFIER WS? extras WS? requirement_details

    Args:
        tokenizer: The Tokenizer to use for parsing.

    Returns:
        A ParsedRequirement object representing the parsed specifier.
    """
    tokenizer.consume("WS")

    name_token = tokenizer.expect(
        "IDENTIFIER", expected="package name at the start of dependency specifier"
    )
    name = name_token.text
    tokenizer.consume("WS")

    extras = _parse_extras(tokenizer)
    tokenizer.consume("WS")

    url, specifier, marker = _parse_requirement_details(tokenizer)
    tokenizer.expect("END", expected="end of dependency specifier")

    return ParsedRequirement(name, url, extras, specifier, marker)


def _parse_requirement_details(
    tokenizer: Tokenizer,
) -> tuple[str, str, MarkerList | None]:
    """Parses the details of a requirement from a tokenizer.

    requirement_details = AT URL (WS requirement_marker?)?
                        | specifier WS? (requirement_marker)?

    Args:
        tokenizer: The Tokenizer to use for parsing.

    Returns:
        A tuple containing the URL, specifier, and marker.
    """
    specifier = ""
    url = ""
    marker = None

    if tokenizer.check("AT"):
        tokenizer.read()
        tokenizer.consume("WS")

        url_start = tokenizer.position
        url = tokenizer.expect("URL", expected="URL after @").text
        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        tokenizer.expect("WS", expected="whitespace after URL")

        # The input might end after whitespace.
        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        marker = _parse_requirement_marker(
            tokenizer, span_start=url_start, after="URL and whitespace"
        )
    else:
        specifier_start = tokenizer.position
        specifier = _parse_specifier(tokenizer)
        tokenizer.consume("WS")

        if tokenizer.check("END", peek=True):
            return (url, specifier, marker)

        marker = _parse_requirement_marker(
            tokenizer,
            span_start=specifier_start,
            after=(
                "version specifier"
                if specifier
                else "name and no valid version specifier"
            ),
        )

    return (url, specifier, marker)


def _parse_requirement_marker(
    tokenizer: Tokenizer, *, span_start: int, after: str
) -> MarkerList:
    """Parses a requirement marker from a tokenizer.

    requirement_marker = SEMICOLON marker WS?

    Args:
        tokenizer: The Tokenizer to use for parsing.
        span_start: The starting position of the marker.
        after: The text after which the marker is expected.

    Returns:
        A MarkerList representing the parsed marker.
    """
    if not tokenizer.check("SEMICOLON"):
        tokenizer.raise_syntax_error(
            f"Expected end or semicolon (after {after})",
            span_start=span_start,
        )
    tokenizer.read()

    marker = _parse_marker(tokenizer)
    tokenizer.consume("WS")

    return marker


def _parse_extras(tokenizer: Tokenizer) -> list[str]:
    """Parses extras from a tokenizer.

    extras = (LEFT_BRACKET wsp* extras_list? wsp* RIGHT_BRACKET)?

    Args:
        tokenizer: The Tokenizer to use for parsing.

    Returns:
        A list of strings representing the parsed extras.
    """
    if not tokenizer.check("LEFT_BRACKET", peek=True):
        return []

    with tokenizer.enclosing_tokens(
        "LEFT_BRACKET",
        "RIGHT_BRACKET",
        around="extras",
    ):
        tokenizer.consume("WS")
        extras = _parse_extras_list(tokenizer)
        tokenizer.consume("WS")

    return extras


def _parse_extras_list(tokenizer: Tokenizer) -> list[str]:
    """Parses a list of extras from a tokenizer.

    extras_list = identifier (wsp* ',' wsp* identifier)*

    Args:
        tokenizer: The Tokenizer to use for parsing.

    Returns:
        A list of strings representing the parsed extras.
    """
    extras: list[str] = []

    if not tokenizer.check("IDENTIFIER"):
        return extras

    extras.append(tokenizer.read().text)

    while True:
        tokenizer.consume("WS")
        if tokenizer.check("IDENTIFIER", peek=True):
            tokenizer.raise_syntax_error("Expected comma between extra names")
        elif not tokenizer.check("COMMA"):
            break

        tokenizer.read()
        tokenizer.consume("WS")

        extra_token = tokenizer.expect("IDENTIFIER", expected="extra name after comma")
        extras.append(extra_token.text)

    return extras


def _parse_specifier(tokenizer: Tokenizer) -> str:
    """Parses a specifier from a tokenizer.

    specifier = LEFT_PARENTHESIS WS? version_many WS? RIGHT_PARENTHESIS
              | WS? version_many WS?

    Args:
        tokenizer: The Tokenizer to use for parsing.

    Returns:
        A string representing the parsed specifier.
    """
    with tokenizer.enclosing_tokens(
        "LEFT_PARENTHESIS",
        "RIGHT_PARENTHESIS",
        around="version specifier",
    ):
        tokenizer.consume("WS")
        parsed_specifiers = _parse_version_many(tokenizer)
        tokenizer.consume("WS")

    return parsed_specifiers


def _parse_version_many(tokenizer: Tokenizer) -> str:
    """Parses a version specifier from a tokenizer.

    version_many = (SPECIFIER (WS? COMMA WS? SPECIFIER)*)?

    Args:
        tokenizer: The Tokenizer to use for parsing.

    Returns:
        A string representing the parsed version specifier.
    """
    parsed_specifiers = ""
    while tokenizer.check("SPECIFIER"):
        span_start = tokenizer.position
        parsed_specifiers += tokenizer.read().text
        if tokenizer.check("VERSION_PREFIX_TRAIL", peek=True):
            tokenizer.raise_syntax_error(
                ".* suffix can only be used with `==` or `!=` operators",
                span_start=span_start,
                span_end=tokenizer.position + 1,
            )
        if tokenizer.check("VERSION_LOCAL_LABEL_TRAIL", peek=True):
            tokenizer.raise_syntax_error(
                "Local version label can only be used with `==` or `!=` operators",
                span_start=span_start,
                span_end=tokenizer.position,
            )
        tokenizer.consume("WS")
        if not tokenizer.check("COMMA"):
            break
        parsed_specifiers += tokenizer.read().text
        tokenizer.consume("WS")

    return parsed_specifiers


# --------------------------------------------------------------------------------------
# Recursive descent parser for marker expression
# --------------------------------------------------------------------------------------
def parse_marker(source: str) -> MarkerList:
    """Parses a marker expression string.

    Args:
        source: The marker expression string to parse.

    Returns:
        A MarkerList representing the parsed marker expression.
    """
    return _parse_full_marker(Tokenizer(source, rules=DEFAULT_RULES))


def _parse_full_marker(tokenizer: Tokenizer) -> MarkerList:
    """Parses a full marker expression from a tokenizer.

    Args:
        tokenizer: The Tokenizer to use for parsing.

    Returns:
        A MarkerList representing the parsed marker expression.
    """
    retval = _parse_marker(tokenizer)
    tokenizer.expect("END", expected="end of marker expression")
    return retval


def _parse_marker(tokenizer: Tokenizer) -> MarkerList:
    """Parses a marker expression from a tokenizer.

    marker = marker_atom (BOOLOP marker_atom)+

    Args:
        tokenizer: The Tokenizer to use for parsing.

    Returns:
        A MarkerList representing the parsed marker expression.
    """
    expression = [_parse_marker_atom(tokenizer)]
    while tokenizer.check("BOOLOP"):
        token = tokenizer.read()
        expr_right = _parse_marker_atom(tokenizer)
        expression.extend((token.text, expr_right))
    return expression


def _parse_marker_atom(tokenizer: Tokenizer) -> MarkerAtom:
    """Parses a marker atom from a tokenizer.

    marker_atom = WS? LEFT_PARENTHESIS WS? marker WS? RIGHT_PARENTHESIS WS?
                | WS? marker_item WS?

    Args:
        tokenizer: The Tokenizer to use for parsing.

    Returns:
        A MarkerAtom representing the parsed marker atom.
    """
    tokenizer.consume("WS")
    if tokenizer.check("LEFT_PARENTHESIS", peek=True):
        with tokenizer.enclosing_tokens(
            "LEFT_PARENTHESIS",
            "RIGHT_PARENTHESIS",
            around="marker expression",
        ):
            tokenizer.consume("WS")
            marker: MarkerAtom = _parse_marker(tokenizer)
            tokenizer.consume("WS")
    else:
        marker = _parse_marker_item(tokenizer)
    tokenizer.consume("WS")
    return marker


def _parse_marker_item(tokenizer: Tokenizer) -> MarkerItem:
    """Parses a marker item from a tokenizer.

    marker_item = WS? marker_var WS? marker_op WS? marker_var WS?

    Args:
        tokenizer: The Tokenizer to use for parsing.

    Returns:
        A MarkerItem representing the parsed marker item.
    """
    tokenizer.consume("WS")
    marker_var_left = _parse_marker_var(tokenizer)
    tokenizer.consume("WS")
    marker_op = _parse_marker_op(tokenizer)
    tokenizer.consume("WS")
    marker_var_right = _parse_marker_var(tokenizer)
    tokenizer.consume("WS")
    return (marker_var_left, marker_op, marker_var_right)


def _parse_marker_var(tokenizer: Tokenizer) -> MarkerVar:
    """Parses a marker variable from a tokenizer.

    marker_var = VARIABLE | QUOTED_STRING

    Args:
        tokenizer: The Tokenizer to use for parsing.

    Returns:
        A MarkerVar representing the parsed marker variable.
    """
    if tokenizer.check("VARIABLE"):
        return process_env_var(tokenizer.read().text.replace(".", "_"))
    elif tokenizer.check("QUOTED_STRING"):
        return process_python_str(tokenizer.read().text)
    else:
        tokenizer.raise_syntax_error(
            message="Expected a marker variable or quoted string"
        )


def process_env_var(env_var: str) -> Variable:
    """Processes an environment variable.

    Args:
        env_var: The environment variable to process.

    Returns:
        A Variable object representing the processed environment variable.
    """
    if env_var in ("platform_python_implementation", "python_implementation"):
        return Variable("platform_python_implementation")
    else:
        return Variable(env_var)


def process_python_str(python_str: str) -> Value:
    """Processes a Python string.

    Args:
        python_str: The Python string to process.

    Returns:
        A Value object representing the processed Python string.
    """
    value = ast.literal_eval(python_str)
    return Value(str(value))


def _parse_marker_op(tokenizer: Tokenizer) -> Op:
    """Parses a marker operator from a tokenizer.

    marker_op = IN | NOT IN | OP

    Args:
        tokenizer: The Tokenizer to use for parsing.

    Returns:
        An Op object representing the parsed marker operator.
    """
    if tokenizer.check("IN"):
        tokenizer.read()
        return Op("in")
    elif tokenizer.check("NOT"):
        tokenizer.read()
        tokenizer.expect("WS", expected="whitespace after 'not'")
        tokenizer.expect("IN", expected="'in' after 'not'")
        return Op("not in")
    elif tokenizer.check("OP"):
        return Op(tokenizer.read().text)
    else:
        return tokenizer.raise_syntax_error(
            "Expected marker operator, one of "
            "<=, <, !=, ==, >=, >, ~=, ===, in, not in"
        )
```
