#!/usr/bin/env python
# pycodestyle.py - Check Python source code formatting, according to
# PEP 8
#
# Copyright (C) 2006-2009 Johann C. Rocholl <johann@rocholl.net>
# Copyright (C) 2009-2014 Florent Xicluna <florent.xicluna@gmail.com>
# Copyright (C) 2014-2016 Ian Lee <ianlee1521@gmail.com>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
r"""
Check Python source code formatting, according to PEP 8.

For usage and a list of options, try this:
$ python pycodestyle.py -h

This program and its regression test suite live here:
https://github.com/pycqa/pycodestyle

Groups of errors and warnings:
E errors
W warnings
100 indentation
200 whitespace
300 blank lines
400 imports
500 line length
600 deprecation
700 statements
900 syntax error
"""
import bisect
import configparser
import inspect
import io
import keyword
import os
import re
import sys
import time
import tokenize
import warnings
from fnmatch import fnmatch
from functools import lru_cache
from optparse import OptionParser

# this is a performance hack.  see https://bugs.python.org/issue43014
if (
        sys.version_info < (3, 10) and
        callable(getattr(tokenize, '_compile', None))
):  # pragma: no cover (<py310)
    tokenize._compile = lru_cache(tokenize._compile)  # type: ignore

__version__ = '2.12.1'

DEFAULT_EXCLUDE = '.svn,CVS,.bzr,.hg,.git,__pycache__,.tox'
DEFAULT_IGNORE = 'E121,E123,E126,E226,E24,E704,W503,W504'
try:
    if sys.platform == 'win32':  # pragma: win32 cover
        USER_CONFIG = os.path.expanduser(r'~\.pycodestyle')
    else:  # pragma: win32 no cover
        USER_CONFIG = os.path.join(
            os.getenv('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'),
            'pycodestyle'
        )
except ImportError:
    USER_CONFIG = None

PROJECT_CONFIG = ('setup.cfg', 'tox.ini')
MAX_LINE_LENGTH = 79
# Number of blank lines between various code parts.
BLANK_LINES_CONFIG = {
    # Top level class and function.
    'top_level': 2,
    # Methods and nested class and function.
    'method': 1,
}
MAX_DOC_LENGTH = 72
INDENT_SIZE = 4
REPORT_FORMAT = {
    'default': '%(path)s:%(row)d:%(col)d: %(code)s %(text)s',
    'pylint': '%(path)s:%(row)d: [%(code)s] %(text)s',
}

PyCF_ONLY_AST = 1024
SINGLETONS = frozenset(['False', 'None', 'True'])
KEYWORDS = frozenset(keyword.kwlist + ['print']) - SINGLETONS
UNARY_OPERATORS = frozenset(['>>', '**', '*', '+', '-'])
ARITHMETIC_OP = frozenset(['**', '*', '/', '//', '+', '-', '@'])
WS_OPTIONAL_OPERATORS = ARITHMETIC_OP.union(['^', '&', '|', '<<', '>>', '%'])
WS_NEEDED_OPERATORS = frozenset([
    '**=', '*=', '/=', '//=', '+=', '-=', '!=', '<', '>',
    '%=', '^=', '&=', '|=', '==', '<=', '>=', '<<=', '>>=', '=',
    'and', 'in', 'is', 'or', '->', ':='])
WHITESPACE = frozenset(' \t\xa0')
NEWLINE = frozenset([tokenize.NL, tokenize.NEWLINE])
SKIP_TOKENS = NEWLINE.union([tokenize.INDENT, tokenize.DEDENT])
# ERRORTOKEN is triggered by backticks in Python 3
SKIP_COMMENTS = SKIP_TOKENS.union([tokenize.COMMENT, tokenize.ERRORTOKEN])
BENCHMARK_KEYS = ['directories', 'files', 'logical lines', 'physical lines']

INDENT_REGEX = re.compile(r'([ \t]*)')
ERRORCODE_REGEX = re.compile(r'\b[A-Z]\d{3}\b')
DOCSTRING_REGEX = re.compile(r'u?r?["\']')
EXTRANEOUS_WHITESPACE_REGEX = re.compile(r'[\[({][ \t]|[ \t][\]}),;:](?!=)')
WHITESPACE_AFTER_DECORATOR_REGEX = re.compile(r'@\s')
WHITESPACE_AFTER_COMMA_REGEX = re.compile(r'[,;:]\s*(?:  |\t)')
COMPARE_SINGLETON_REGEX = re.compile(r'(\bNone|\bFalse|\bTrue)?\s*([=!]=)'
                                     r'\s*(?(1)|(None|False|True))\b')
COMPARE_NEGATIVE_REGEX = re.compile(r'\b(?<!is\s)(not)\s+[^][)(}{ ]+\s+'
                                    r'(in|is)\s')
COMPARE_TYPE_REGEX = re.compile(
    r'[=!]=\s+type(?:\s*\(\s*([^)]*[^\s)])\s*\))'
    r'|(?<!\.)\btype(?:\s*\(\s*([^)]*[^\s)])\s*\))\s+[=!]='
)
KEYWORD_REGEX = re.compile(r'(\s*)\b(?:%s)\b(\s*)' % r'|'.join(KEYWORDS))
OPERATOR_REGEX = re.compile(r'(?:[^,\s])(\s*)(?:[-+*/|!<=>%&^]+|:=)(\s*)')
LAMBDA_REGEX = re.compile(r'\blambda\b')
HUNK_REGEX = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@.*$')
STARTSWITH_DEF_REGEX = re.compile(r'^(async\s+def|def)\b')
STARTSWITH_TOP_LEVEL_REGEX = re.compile(r'^(async\s+def\s+|def\s+|class\s+|@)')
STARTSWITH_INDENT_STATEMENT_REGEX = re.compile(
    r'^\s*({})\b'.format('|'.join(s.replace(' ', r'\s+') for s in (
        'def', 'async def',
        'for', 'async for',
        'if', 'elif', 'else',
        'try', 'except', 'finally',
        'with', 'async with',
        'class',
        'while',
    )))
)
DUNDER_REGEX = re.compile(r"^__([^\s]+)__(?::\s*[a-zA-Z.0-9_\[\]\"]+)? = ")
BLANK_EXCEPT_REGEX = re.compile(r"except\s*:")

if sys.version_info >= (3, 12):  # pragma: >=3.12 cover
    FSTRING_START = tokenize.FSTRING_START
    FSTRING_MIDDLE = tokenize.FSTRING_MIDDLE
    FSTRING_END = tokenize.FSTRING_END
else:  # pragma: <3.12 cover
    FSTRING_START = FSTRING_MIDDLE = FSTRING_END = -1

_checks = {'physical_line': {}, 'logical_line': {}, 'tree': {}}


def _get_parameters(function):
    return [parameter.name
            for parameter
            in inspect.signature(function).parameters.values()
            if parameter.kind == parameter.POSITIONAL_OR_KEYWORD]


def register_check(check, codes=None):
    """Register a new check object."""
    def _add_check(check, kind, codes, args):
        if check in _checks[kind]:
            _checks[kind][check][0].extend(codes or [])
        else:
            _checks[kind][check] = (codes or [''], args)
    if inspect.isfunction(check):
        args = _get_parameters(check)
        if args and args[0] in ('physical_line', 'logical_line'):
            if codes is None:
                codes = ERRORCODE_REGEX.findall(check.__doc__ or '')
            _add_check(check, args[0], codes, args)
    elif inspect.isclass(check):
        if _get_parameters(check.__init__)[:2] == ['self', 'tree']:
            _add_check(check, 'tree', codes, None)
    return check


########################################################################
# Plugins (check functions) for physical lines
########################################################################

@register_check
def tabs_or_spaces(physical_line, indent_char):
    r"""Never mix tabs and spaces.

    The most popular way of indenting Python is with spaces only.  The
    second-most popular way is with tabs only.  Code indented with a
    mixture of tabs and spaces should be converted to using spaces
    exclusively.  When invoking the Python command line interpreter with
    the -t option, it issues warnings about code that illegally mixes
    tabs and spaces.  When using -tt these warnings become errors.
    These options are highly recommended!

    Okay: if a == 0:\n    a = 1\n    b = 1
    """
    indent = INDENT_REGEX.match(physical_line).group(1)
    for offset, char in enumerate(indent):
        if char != indent_char:
            return offset, "E101 indentation contains mixed spaces and tabs"


@register_check
def tabs_obsolete(physical_line):
    r"""On new projects, spaces-only are strongly recommended over tabs.

    Okay: if True:\n    return
    W191: if True:\n\treturn
    """
    indent = INDENT_REGEX.match(physical_line).group(1)
    if '\t' in indent:
        return indent.index('\t'), "W191 indentation contains tabs"


@register_check
def trailing_whitespace(physical_line):
    r"""Trailing whitespace is superfluous.

    The warning returned varies on whether the line itself is blank,
    for easier filtering for those who want to indent their blank lines.

    Okay: spam(1)\n#
    W291: spam(1) \n#
    W293: class Foo(object):\n    \n    bang = 12
    """
    physical_line = physical_line.rstrip('\n')    # chr(10), newline
    physical_line = physical_line.rstrip('\r')    # chr(13), carriage return
    physical_line = physical_line.rstrip('\x0c')  # chr(12), form feed, ^L
    stripped = physical_line.rstrip(' \t\v')
    if physical_line != stripped:
        if stripped:
            return len(stripped), "W291 trailing whitespace"
        else:
            return 0, "W293 blank line contains whitespace"


@register_check
def trailing_blank_lines(physical_line, lines, line_number, total_lines):
    r"""Trailing blank lines are superfluous.

    Okay: spam(1)
    W391: spam(1)\n

    However the last line should end with a new line (warning W292).
    """
    if line_number == total_lines:
        stripped_last_line = physical_line.rstrip('\r\n')
        if physical_line and not stripped_last_line:
            return 0, "W391 blank line at end of file"
        if stripped_last_line == physical_line:
            return len(lines[-1]), "W292 no newline at end of file"


@register_check
def maximum_line_length(physical_line, max_line_length, multiline,
                        line_number, noqa):
    r"""Limit all lines to a maximum of 79 characters.

    There are still many devices around that are limited to 80 character
    lines; plus, limiting windows to 80 characters makes it possible to
    have several windows side-by-side.  The default wrapping on such
    devices looks ugly.  Therefore, please limit all lines to a maximum
    of 79 characters. For flowing long blocks of text (docstrings or
    comments), limiting the length to 72 characters is recommended.

    Reports error E501.
    """
    line = physical_line.rstrip()
    length = len(line)
    if length > max_line_length and not noqa:
        # Special case: ignore long shebang lines.
        if line_number == 1 and line.startswith('#!'):
            return
        # Special case for long URLs in multi-line docstrings or
        # comments, but still report the error when the 72 first chars
        # are whitespaces.
        chunks = line.split()
        if ((len(chunks) == 1 and multiline) or
            (len(chunks) == 2 and chunks[0] == '#')) and \
                len(line) - len(chunks[-1]) < max_line_length - 7:
            return
        if length > max_line_length:
            return (max_line_length, "E501 line too long "
                    "(%d > %d characters)" % (length, max_line_length))


########################################################################
# Plugins (check functions) for logical lines
########################################################################


def _is_one_liner(logical_line, indent_level, lines, line_number):
    if not STARTSWITH_TOP_LEVEL_REGEX.match(logical_line):
        return False

    line_idx = line_number - 1

    if line_idx < 1:
        prev_indent = 0
    else:
        prev_indent = expand_indent(lines[line_idx - 1])

    if prev_indent > indent_level:
        return False

    while line_idx < len(lines):
        line = lines[line_idx].strip()
        if not line.startswith('@') and STARTSWITH_TOP_LEVEL_REGEX.match(line):
            break
        else:
            line_idx += 1
    else:
        return False  # invalid syntax: EOF while searching for def/class

    next_idx = line_idx + 1
    while next_idx < len(lines):
        if lines[next_idx].strip():
            break
        else:
            next_idx += 1
    else:
        return True  # line is last in the file

    return expand_indent(lines[next_idx]) <= indent_level


@register_check
def blank_lines(logical_line, blank_lines, indent_level, line_number,
                blank_before, previous_logical,
                previous_unindented_logical_line, previous_indent_level,
                lines):
    r"""Separate top-level function and class definitions with two blank
    lines.

    Method definitions inside a class are separated by a single blank
    line.

    Extra blank lines may be used (sparingly) to separate groups of
    related functions.  Blank lines may be omitted between a bunch of
    related one-liners (e.g. a set of dummy implementations).

    Use blank lines in functions, sparingly, to indicate logical
    sections.

    Okay: def a():\n    pass\n\n\ndef b():\n    pass
    Okay: def a():\n    pass\n\n\nasync def b():\n    pass
    Okay: def a():\n    pass\n\n\n# Foo\n# Bar\n\ndef b():\n    pass
    Okay: default = 1\nfoo = 1
    Okay: classify = 1\nfoo = 1

    E301: class Foo:\n    b = 0\n    def bar():\n        pass
    E302: def a():\n    pass\n\ndef b(n):\n    pass
    E302: def a():\n    pass\n\nasync def b(n):\n    pass
    E303: def a():\n    pass\n\n\n\ndef b(n):\n    pass
    E303: def a():\n\n\n\n    pass
    E304: @decorator\n\ndef a():\n    pass
    E305: def a():\n    pass\na()
    E306: def a():\n    def b():\n        pass\n    def c():\n        pass
    """  # noqa
    top_level_lines = BLANK_LINES_CONFIG['top_level']
    method_lines = BLANK_LINES_CONFIG['method']

    if not previous_logical and blank_before < top_level_lines:
        return  # Don't expect blank lines before the first line
    if previous_logical.startswith('@'):
        if blank_lines:
            yield 0, "E304 blank lines found after function decorator"
    elif (blank_lines > top_level_lines or
            (indent_level and blank_lines == method_lines + 1)
          ):
        yield 0, "E303 too many blank lines (%d)" % blank_lines
    elif STARTSWITH_TOP_LEVEL_REGEX.match(logical_line):
        # allow a group of one-liners
        if (
            _is_one_liner(logical_line, indent_level, lines, line_number) and
            blank_before == 0
        ):
            return
        if indent_level:
            if not (blank_before == method_lines or
                    previous_indent_level < indent_level or
                    DOCSTRING_REGEX.match(previous_logical)
                    ):
                ancestor_level = indent_level
                nested = False
                # Search backwards for a def ancestor or tree root
                # (top level).
                for line in lines[line_number - top_level_lines::-1]:
                    if line.strip() and expand_indent(line) < ancestor_level:
                        ancestor_level = expand_indent(line)
                        nested = STARTSWITH_DEF_REGEX.match(line.lstrip())
                        if nested or ancestor_level == 0:
                            break
                if nested:
                    yield 0, "E306 expected %s blank line before a " \
                        "nested definition, found 0" % (method_lines,)
                else:
                    yield 0, "E301 expected {} blank line, found 0".format(
                        method_lines)
        elif blank_before != top_level_lines:
            yield 0, "E302 expected %s blank lines, found %d" % (
                top_level_lines, blank_before)
    elif (logical_line and
            not indent_level and
            blank_before != top_level_lines and
            previous_unindented_logical_line.startswith(('def ', 'class '))
          ):
        yield 0, "E305 expected %s blank lines after " \
            "class or function definition, found %d" % (
                top_level_lines, blank_before)


@register_check
def extraneous_whitespace(logical_line):
    r"""Avoid extraneous whitespace.

    Avoid extraneous whitespace in these situations:
    - Immediately inside parentheses, brackets or braces.
    - Immediately before a comma, semicolon, or colon.

    Okay: spam(ham[1], {eggs: 2})
    E201: spam( ham[1], {eggs: 2})
    E201: spam(ham[ 1], {eggs: 2})
    E201: spam(ham[1], { eggs: 2})
    E202: spam(ham[1], {eggs: 2} )
    E202: spam(ham[1 ], {eggs: 2})
    E202: spam(ham[1], {eggs: 2 })

    E203: if x == 4: print x, y; x, y = y , x
    E203: if x == 4: print x, y ; x, y = y, x
    E203: if x == 4 : print x, y; x, y = y, x

    Okay: @decorator
    E204: @ decorator
    """
    line = logical_line
    for match in EXTRANEOUS_WHITESPACE_REGEX.finditer(line):
        text = match.group()
        char = text.strip()
        found = match.start()
        if text[-1].isspace():
            # assert char in '([{'
            yield found + 1, "E201 whitespace after '%s'" % char
        elif line[found - 1] != ',':
            code = ('E202' if char in '}])' else 'E203')  # if char in ',;:'
            yield found, f"{code} whitespace before '{char}'"

    if WHITESPACE_AFTER_DECORATOR_REGEX.match(logical_line):
        yield 1, "E204 whitespace after decorator '@'"


@register_check
def whitespace_around_keywords(logical_line):
    r"""Avoid extraneous whitespace around keywords.

    Okay: True and False
    E271: True and  False
    E272: True  and False
    E273: True and\tFalse
    E274: True\tand False
    """
    for match in KEYWORD_REGEX.finditer(logical_line):
        before, after = match.groups()

        if '\t' in before:
            yield match.start(1), "E274 tab before keyword"
        elif len(before) > 1:
            yield match.start(1), "E272 multiple spaces before keyword"

        if '\t' in after:
            yield match.start(2), "E273 tab after keyword"
        elif len(after) > 1:
            yield match.start(2), "E271 multiple spaces after keyword"


@register_check
def missing_whitespace_after_keyword(logical_line, tokens):
    r"""Keywords should be followed by whitespace.

    Okay: from foo import (bar, baz)
    E275: from foo import(bar, baz)
    E275: from importable.module import(bar, baz)
    E275: if(foo): bar
    """
    for tok0, tok1 in zip(tokens, tokens[1:]):
        # This must exclude the True/False/None singletons, which can
        # appear e.g. as "if x is None:", and async/await, which were
        # valid identifier names in old Python versions.
        if (tok0.end == tok1.start and
                tok0.type == tokenize.NAME and
                keyword.iskeyword(tok0.string) and
                tok0.string not in SINGLETONS and
                not (tok0.string == 'except' and tok1.string == '*') and
                not (tok0.string == 'yield' and tok1.string == ')') and
                tok1.string not in ':\n'):
            yield tok0.end, "E275 missing whitespace after keyword"


@register_check
def indentation(logical_line, previous_logical, indent_char,
                indent_level, previous_indent_level,
                indent_size):
    r"""Use indent_size (PEP8 says 4) spaces per indentation level.

    For really old code that you don't want to mess up, you can continue
    to use 8-space tabs.

    Okay: a = 1
    Okay: if a == 0:\n    a = 1
    E111:   a = 1
    E114:   # a = 1

    Okay: for item in items:\n    pass
    E112: for item in items:\npass
    E115: for item in items:\n# Hi\n    pass

    Okay: a = 1\nb = 2
    E113: a = 1\n    b = 2
    E116: a = 1\n    # b = 2
    """
    c = 0 if logical_line else 3
    tmpl = "E11%d %s" if logical_line else "E11%d %s (comment)"
    if indent_level % indent_size:
        yield 0, tmpl % (
            1 + c,
            "indentation is not a multiple of " + str(indent_size),
        )
    indent_expect = previous_logical.endswith(':')
    if indent_expect and indent_level <= previous_indent_level:
        yield 0, tmpl % (2 + c, "expected an indented block")
    elif not indent_expect and indent_level > previous_indent_level:
        yield 0, tmpl % (3 + c, "unexpected indentation")

    if indent_expect:
        expected_indent_amount = 8 if indent_char == '\t' else 4
        expected_indent_level = previous_indent_level + expected_indent_amount
        if indent_level > expected_indent_level:
            yield 0, tmpl % (7, 'over-indented')


@register_check
def continued_indentation(logical_line, tokens, indent_level, hang_closing,
                          indent_char, indent_size, noqa, verbose):
    r"""Continuation lines indentation.

    Continuation lines should align wrapped elements either vertically
    using Python's implicit line joining inside parentheses, brackets
    and braces, or using a hanging indent.

    When using a hanging indent these considerations should be applied:
    - there should be no arguments on the first line, and
    - further indentation should be used to clearly distinguish itself
      as a continuation line.

    Okay: a = (\n)
    E123: a = (\n    )

    Okay: a = (\n    42)
    E121: a = (\n   42)
    E122: a = (\n42)
    E123: a = (\n    42\n    )
    E124: a = (24,\n     42\n)
    E125: if (\n    b):\n    pass
    E126: a = (\n        42)
    E127: a = (24,\n      42)
    E128: a = (24,\n    42)
    E129: if (a or\n    b):\n    pass
    E131: a = (\n    42\n 24)
    """
    first_row = tokens[0][2][0]
    nrows = 1 + tokens[-1][2][0] - first_row
    if noqa or nrows == 1:
        return

    # indent_next tells us whether the next block is indented; assuming
    # that it is indented by 4 spaces, then we should not allow 4-space
    # indents on the final continuation line; in turn, some other
    # indents are allowed to have an extra 4 spaces.
    indent_next = logical_line.endswith(':')

    row = depth = 0
    valid_hangs = (indent_size,) if indent_char != '\t' \
        else (indent_size, indent_size * 2)
    # remember how many brackets were opened on each line
    parens = [0] * nrows
    # relative indents of physical lines
    rel_indent = [0] * nrows
    # for each depth, collect a list of opening rows
    open_rows = [[0]]
    # for each depth, memorize the hanging indentation
    hangs = [None]
    # visual indents
    indent_chances = {}
    last_indent = tokens[0][2]
    visual_indent = None
    last_token_multiline = False
    # for each depth, memorize the visual indent column
    indent = [last_indent[1]]
    if verbose >= 3:
        print(">>> " + tokens[0][4].rstrip())

    for token_type, text, start, end, line in tokens:

        newline = row < start[0] - first_row
        if newline:
            row = start[0] - first_row
            newline = not last_token_multiline and token_type not in NEWLINE

        if newline:
            # this is the beginning of a continuation line.
            last_indent = start
            if verbose >= 3:
                print("... " + line.rstrip())

            # record the initial indent.
            rel_indent[row] = expand_indent(line) - indent_level

            # identify closing bracket
            close_bracket = (token_type == tokenize.OP and text in ']})')

            # is the indent relative to an opening bracket line?
            for open_row in reversed(open_rows[depth]):
                hang = rel_indent[row] - rel_indent[open_row]
                hanging_indent = hang in valid_hangs
                if hanging_indent:
                    break
            if hangs[depth]:
                hanging_indent = (hang == hangs[depth])
            # is there any chance of visual indent?
            visual_indent = (not close_bracket and hang > 0 and
                             indent_chances.get(start[1]))

            if close_bracket and indent[depth]:
                # closing bracket for visual indent
                if start[1] != indent[depth]:
                    yield (start, "E124 closing bracket does not match "
                           "visual indentation")
            elif close_bracket and not hang:
                # closing bracket matches indentation of opening
                # bracket's line
                if hang_closing:
                    yield start, "E133 closing bracket is missing indentation"
            elif indent[depth] and start[1] < indent[depth]:
                if visual_indent is not True:
                    # visual indent is broken
                    yield (start, "E128 continuation line "
                           "under-indented for visual indent")
            elif hanging_indent or (indent_next and
                                    rel_indent[row] == 2 * indent_size):
                # hanging indent is verified
                if close_bracket and not hang_closing:
                    yield (start, "E123 closing bracket does not match "
                           "indentation of opening bracket's line")
                hangs[depth] = hang
            elif visual_indent is True:
                # visual indent is verified
                indent[depth] = start[1]
            elif visual_indent in (text, str):
                # ignore token lined up with matching one from a
                # previous line
                pass
            else:
                # indent is broken
                if hang <= 0:
                    error = "E122", "missing indentation or outdented"
                elif indent[depth]:
                    error = "E127", "over-indented for visual indent"
                elif not close_bracket and hangs[depth]:
                    error = "E131", "unaligned for hanging indent"
                else:
                    hangs[depth] = hang
                    if hang > indent_size:
                        error = "E126", "over-indented for hanging indent"
                    else:
                        error = "E121", "under-indented for hanging indent"
                yield start, "%s continuation line %s" % error

        # look for visual indenting
        if (parens[row] and
                token_type not in (tokenize.NL, tokenize.COMMENT) and
                not indent[depth]):
            indent[depth] = start[1]
            indent_chances[start[1]] = True
            if verbose >= 4:
                print(f"bracket depth {depth} indent to {start[1]}")
        # deal with implicit string concatenation
        elif token_type in (tokenize.STRING, tokenize.COMMENT, FSTRING_START):
            indent_chances[start[1]] = str
        # visual indent after assert/raise/with
        elif not row and not depth and text in ["assert", "raise", "with"]:
            indent_chances[end[1] + 1] = True
        # special case for the "if" statement because len("if (") == 4
        elif not indent_chances and not row and not depth and text == 'if':
            indent_chances[end[1] + 1] = True
        elif text == ':' and line[end[1]:].isspace():
            open_rows[depth].append(row)

        # keep track of bracket depth
        if token_type == tokenize.OP:
            if text in '([{':
                depth += 1
                indent.append(0)
                hangs.append(None)
                if len(open_rows) == depth:
                    open_rows.append([])
                open_rows[depth].append(row)
                parens[row] += 1
                if verbose >= 4:
                    print("bracket depth %s seen, col %s, visual min = %s" %
                          (depth, start[1], indent[depth]))
            elif text in ')]}' and depth > 0:
                # parent indents should not be more than this one
                prev_indent = indent.pop() or last_indent[1]
                hangs.pop()
                for d in range(depth):
                    if indent[d] > prev_indent:
                        indent[d] = 0
                for ind in list(indent_chances):
                    if ind >= prev_indent:
                        del indent_chances[ind]
                del open_rows[depth + 1:]
                depth -= 1
                if depth:
                    indent_chances[indent[depth]] = True
                for idx in range(row, -1, -1):
                    if parens[idx]:
                        parens[idx] -= 1
                        break
            assert len(indent) == depth + 1
            if start[1] not in indent_chances:
                # allow lining up tokens
                indent_chances[start[1]] = text

        last_token_multiline = (start[0] != end[0])
        if last_token_multiline:
            rel_indent[end[0] - first_row] = rel_indent[row]

    if indent_next and expand_indent(line) == indent_level + indent_size:
        pos = (start[0], indent[0] + indent_size)
        if visual_indent:
            code = "E129 visually indented line"
        else:
            code = "E125 continuation line"
        yield pos, "%s with same indent as next logical line" % code


@register_check
def whitespace_before_parameters(logical_line, tokens):
    r"""Avoid extraneous whitespace.

    Avoid extraneous whitespace in the following situations:
    - before the open parenthesis that starts the argument list of a
      function call.
    - before the open parenthesis that starts an indexing or slicing.

    Okay: spam(1)
    E211: spam (1)

    Okay: dict['key'] = list[index]
    E211: dict ['key'] = list[index]
    E211: dict['key'] = list [index]
    """
    prev_type, prev_text, __, prev_end, __ = tokens[0]
    for index in range(1, len(tokens)):
        token_type, text, start, end, __ = tokens[index]
        if (
            token_type == tokenize.OP and
            text in '([' and
            start != prev_end and
            (prev_type == tokenize.NAME or prev_text in '}])') and
            # Syntax "class A (B):" is allowed, but avoid it
            (index < 2 or tokens[index - 2][1] != 'class') and
            # Allow "return (a.foo for a in range(5))"
            not keyword.iskeyword(prev_text) and
            (
                sys.version_info < (3, 9) or
                # 3.12+: type is a soft keyword but no braces after
                prev_text == 'type' or
                not keyword.issoftkeyword(prev_text)
            )
        ):
            yield prev_end, "E211 whitespace before '%s'" % text
        prev_type = token_type
        prev_text = text
        prev_end = end


@register_check
def whitespace_around_operator(logical_line):
    r"""Avoid extraneous whitespace around an operator.

    Okay: a = 12 + 3
    E221: a = 4  + 5
    E222: a = 4 +  5
    E223: a = 4\t+ 5
    E224: a = 4 +\t5
    """
    for match in OPERATOR_REGEX.finditer(logical_line):
        before, after = match.groups()

        if '\t' in before:
            yield match.start(1), "E223 tab before operator"
        elif len(before) > 1:
            yield match.start(1), "E221 multiple spaces before operator"

        if '\t' in after:
            yield match.start(2), "E224 tab after operator"
        elif len(after) > 1:
            yield match.start(2), "E222 multiple spaces after operator"


@register_check
def missing_whitespace(logical_line, tokens):
    r"""Surround operators with the correct amount of whitespace.

    - Always surround these binary operators with a single space on
      either side: assignment (=), augmented assignment (+=, -= etc.),
      comparisons (==, <, >, !=, <=, >=, in, not in, is, is not),
      Booleans (and, or, not).

    - Each comma, semicolon or colon should be followed by whitespace.

    - If operators with different priorities are used, consider adding
      whitespace around the operators with the lowest priorities.

    Okay: i = i + 1
    Okay: submitted += 1
    Okay: x = x * 2 - 1
    Okay: hypot2 = x * x + y * y
    Okay: c = (a + b) * (a - b)
    Okay: foo(bar, key='word', *args, **kwargs)
    Okay: alpha[:-i]
    Okay: [a, b]
    Okay: (3,)
    Okay: a[3,] = 1
    Okay: a[1:4]
    Okay: a[:4]
    Okay: a[1:]
    Okay: a[1:4:2]

    E225: i=i+1
    E225: submitted +=1
    E225: x = x /2 - 1
    E225: z = x **y
    E225: z = 1and 1
    E226: c = (a+b) * (a-b)
    E226: hypot2 = x*x + y*y
    E227: c = a|b
    E228: msg = fmt%(errno, errmsg)
    E231: ['a','b']
    E231: foo(bar,baz)
    E231: [{'a':'b'}]
    """
    need_space = False
    prev_type = tokenize.OP
    prev_text = prev_end = None
    operator_types = (tokenize.OP, tokenize.NAME)
    brace_stack = []
    for token_type, text, start, end, line in tokens:
        if token_type == tokenize.OP and text in {'[', '(', '{'}:
            brace_stack.append(text)
        elif token_type == FSTRING_START:  # pragma: >=3.12 cover
            brace_stack.append('f')
        elif token_type == tokenize.NAME and text == 'lambda':
            brace_stack.append('l')
        elif brace_stack:
            if token_type == tokenize.OP and text in {']', ')', '}'}:
                brace_stack.pop()
            elif token_type == FSTRING_END:  # pragma: >=3.12 cover
                brace_stack.pop()
            elif (
                    brace_stack[-1] == 'l' and
                    token_type == tokenize.OP and
                    text == ':'
            ):
                brace_stack.pop()

        if token_type in SKIP_COMMENTS:
            continue

        if token_type == tokenize.OP and text in {',', ';', ':'}:
            next_char = line[end[1]:end[1] + 1]
            if next_char not in WHITESPACE and next_char not in '\r\n':
                # slice
                if text == ':' and brace_stack[-1:] == ['[']:
                    pass
                # 3.12+ fstring format specifier
                elif text == ':' and brace_stack[-2:] == ['f', '{']:  # pragma: >=3.12 cover  # noqa: E501
                    pass
                # tuple (and list for some reason?)
                elif text == ',' and next_char in ')]':
                    pass
                else:
                    yield start, f'E231 missing whitespace after {text!r}'

        if need_space:
            if start != prev_end:
                # Found a (probably) needed space
                if need_space is not True and not need_space[1]:
                    yield (need_space[0],
                           "E225 missing whitespace around operator")
                need_space = False
            elif (
                    # def f(a, /, b):
                    #           ^
                    # def f(a, b, /):
                    #              ^
                    # f = lambda a, /:
                    #                ^
                    prev_text == '/' and text in {',', ')', ':'} or
                    # def f(a, b, /):
                    #               ^
                    prev_text == ')' and text == ':'
            ):
                # Tolerate the "/" operator in function definition
                # For more info see PEP570
                pass
            else:
                if need_space is True or need_space[1]:
                    # A needed trailing space was not found
                    yield prev_end, "E225 missing whitespace around operator"
                elif prev_text != '**':
                    code, optype = 'E226', 'arithmetic'
                    if prev_text == '%':
                        code, optype = 'E228', 'modulo'
                    elif prev_text not in ARITHMETIC_OP:
                        code, optype = 'E227', 'bitwise or shift'
                    yield (need_space[0], "%s missing whitespace "
                           "around %s operator" % (code, optype))
                need_space = False
        elif token_type in operator_types and prev_end is not None:
            if (
                    text == '=' and (
                        # allow lambda default args: lambda x=None: None
                        brace_stack[-1:] == ['l'] or
                        # allow keyword args or defaults: foo(bar=None).
                        brace_stack[-1:] == ['('] or
                        # allow python 3.8 fstring repr specifier
                        brace_stack[-2:] == ['f', '{']
                    )
            ):
                pass
            elif text in WS_NEEDED_OPERATORS:
                need_space = True
            elif text in UNARY_OPERATORS:
                # Check if the operator is used as a binary operator
                # Allow unary operators: -123, -x, +1.
                # Allow argument unpacking: foo(*args, **kwargs).
                if prev_type == tokenize.OP and prev_text in '}])' or (
                    prev_type != tokenize.OP and
                    prev_text not in KEYWORDS and (
                        sys.version_info < (3, 9) or
                        not keyword.issoftkeyword(prev_text)
                    )
                ):
                    need_space = None
            elif text in WS_OPTIONAL_OPERATORS:
                need_space = None

            if need_space is None:
                # Surrounding space is optional, but ensure that
                # trailing space matches opening space
                need_space = (prev_end, start != prev_end)
            elif need_space and start == prev_end:
                # A needed opening space was not found
                yield prev_end, "E225 missing whitespace around operator"
                need_space = False
        prev_type = token_type
        prev_text = text
        prev_end = end


@register_check
def whitespace_around_comma(logical_line):
    r"""Avoid extraneous whitespace after a comma or a colon.

    Note: these checks are disabled by default

    Okay: a = (1, 2)
    E241: a = (1,  2)
    E242: a = (1,\t2)
    """
    line = logical_line
    for m in WHITESPACE_AFTER_COMMA_REGEX.finditer(line):
        found = m.start() + 1
        if '\t' in m.group():
            yield found, "E242 tab after '%s'" % m.group()[0]
        else:
            yield found, "E241 multiple spaces after '%s'" % m.group()[0]


@register_check
def whitespace_around_named_parameter_equals(logical_line, tokens):
    r"""Don't use spaces around the '=' sign in function arguments.

    Don't use spaces around the '=' sign when used to indicate a
    keyword argument or a default parameter value, except when
    using a type annotation.

    Okay: def complex(real, imag=0.0):
    Okay: return magic(r=real, i=imag)
    Okay: boolean(a == b)
    Okay: boolean(a != b)
    Okay: boolean(a <= b)
    Okay: boolean(a >= b)
    Okay: def foo(arg: int = 42):
    Okay: async def foo(arg: int = 42):

    E251: def complex(real, imag = 0.0):
    E251: return magic(r = real, i = imag)
    E252: def complex(real, image: float=0.0):
    """
    parens = 0
    no_space = False
    require_space = False
    prev_end = None
    annotated_func_arg = False
    in_def = bool(STARTSWITH_DEF_REGEX.match(logical_line))

    message = "E251 unexpected spaces around keyword / parameter equals"
    missing_message = "E252 missing whitespace around parameter equals"

    for token_type, text, start, end, line in tokens:
        if token_type == tokenize.NL:
            continue
        if no_space:
            no_space = False
            if start != prev_end:
                yield (prev_end, message)
        if require_space:
            require_space = False
            if start == prev_end:
                yield (prev_end, missing_message)
        if token_type == tokenize.OP:
            if text in '([':
                parens += 1
            elif text in ')]':
                parens -= 1
            elif in_def and text == ':' and parens == 1:
                annotated_func_arg = True
            elif parens == 1 and text == ',':
                annotated_func_arg = False
            elif parens and text == '=':
                if annotated_func_arg and parens == 1:
                    require_space = True
                    if start == prev_end:
                        yield (prev_end, missing_message)
                else:
                    no_space = True
                    if start != prev_end:
                        yield (prev_end, message)
            if not parens:
                annotated_func_arg = False

        prev_end = end


@register_check
def whitespace_before_comment(logical_line, tokens):
    """Separate inline comments by at least two spaces.

    An inline comment is a comment on the same line as a statement.
    Inline comments should be separated by at least two spaces from the
    statement. They should start with a # and a single space.

    Each line of a block comment starts with a # and one or multiple
    spaces as there can be indented text inside the comment.

    Okay: x = x + 1  # Increment x
    Okay: x = x + 1    # Increment x
    Okay: # Block comments:
    Okay: #  - Block comment list
    Okay: # \xa0- Block comment list
    E261: x = x + 1 # Increment x
    E262: x = x + 1  #Increment x
    E262: x = x + 1  #  Increment x
    E262: x = x + 1  # \xa0Increment x
    E265: #Block comment
    E266: ### Block comment
    """
    prev_end = (0, 0)
    for token_type, text, start, end, line in tokens:
        if token_type == tokenize.COMMENT:
            inline_comment = line[:start[1]].strip()
            if inline_comment:
                if prev_end[0] == start[0] and start[1] < prev_end[1] + 2:
                    yield (prev_end,
                           "E261 at least two spaces before inline comment")
            symbol, sp, comment = text.partition(' ')
            bad_prefix = symbol not in '#:' and (symbol.lstrip('#')[:1] or '#')
            if inline_comment:
                if bad_prefix or comment[:1] in WHITESPACE:
                    yield start, "E262 inline comment should start with '# '"
            elif bad_prefix and (bad_prefix != '!' or start[0] > 1):
                if bad_prefix != '#':
                    yield start, "E265 block comment should start with '# '"
                elif comment:
                    yield start, "E266 too many leading '#' for block comment"
        elif token_type != tokenize.NL:
            prev_end = end


@register_check
def imports_on_separate_lines(logical_line):
    r"""Place imports on separate lines.

    Okay: import os\nimport sys
    E401: import sys, os

    Okay: from subprocess import Popen, PIPE
    Okay: from myclas import MyClass
    Okay: from foo.bar.yourclass import YourClass
    Okay: import myclass
    Okay: import foo.bar.yourclass
    """
    line = logical_line
    if line.startswith('import '):
        found = line.find(',')
        if -1 < found and ';' not in line[:found]:
            yield found, "E401 multiple imports on one line"


@register_check
def module_imports_on_top_of_file(
        logical_line, indent_level, checker_state, noqa):
    r"""Place imports at the top of the file.

    Always put imports at the top of the file, just after any module
    comments and docstrings, and before module globals and constants.

    Okay: import os
    Okay: # this is a comment\nimport os
    Okay: '''this is a module docstring'''\nimport os
    Okay: r'''this is a module docstring'''\nimport os
    E402: a=1\nimport os
    E402: 'One string'\n"Two string"\nimport os
    E402: a=1\nfrom sys import x

    Okay: if x:\n    import os
    """  # noqa
    def is_string_literal(line):
        if line[0] in 'uUbB':
            line = line[1:]
        if line and line[0] in 'rR':
            line = line[1:]
        return line and (line[0] == '"' or line[0] == "'")

    allowed_keywords = (
        'try', 'except', 'else', 'finally', 'with', 'if', 'elif')

    if indent_level:  # Allow imports in conditional statement/function
        return
    if not logical_line:  # Allow empty lines or comments
        return
    if noqa:
        return
    line = logical_line
    if line.startswith('import ') or line.startswith('from '):
        if checker_state.get('seen_non_imports', False):
            yield 0, "E402 module level import not at top of file"
    elif re.match(DUNDER_REGEX, line):
        return
    elif any(line.startswith(kw) for kw in allowed_keywords):
        # Allow certain keywords intermixed with imports in order to
        # support conditional or filtered importing
        return
    elif is_string_literal(line):
        # The first literal is a docstring, allow it. Otherwise, report
        # error.
        if checker_state.get('seen_docstring', False):
            checker_state['seen_non_imports'] = True
        else:
            checker_state['seen_docstring'] = True
    else:
        checker_state['seen_non_imports'] = True


@register_check
def compound_statements(logical_line):
    r"""Compound statements (on the same line) are generally
    discouraged.

    While sometimes it's okay to put an if/for/while with a small body
    on the same line, never do this for multi-clause statements.
    Also avoid folding such long lines!

    Always use a def statement instead of an assignment statement that
    binds a lambda expression directly to a name.

    Okay: if foo == 'blah':\n    do_blah_thing()
    Okay: do_one()
    Okay: do_two()
    Okay: do_three()

    E701: if foo == 'blah': do_blah_thing()
    E701: for x in lst: total += x
    E701: while t < 10: t = delay()
    E701: if foo == 'blah': do_blah_thing()
    E701: else: do_non_blah_thing()
    E701: try: something()
    E701: finally: cleanup()
    E701: if foo == 'blah': one(); two(); three()
    E702: do_one(); do_two(); do_three()
    E703: do_four();  # useless semicolon
    E704: def f(x): return 2*x
    E731: f = lambda x: 2*x
    """
    line = logical_line
    last_char = len(line) - 1
    found = line.find(':')
    prev_found = 0
    counts = {char: 0 for char in '{}[]()'}
    while -1 < found < last_char:
        update_counts(line[prev_found:found], counts)
        if (
                counts['{'] <= counts['}'] and  # {'a': 1} (dict)
                counts['['] <= counts[']'] and  # [1:2] (slice)
                counts['('] <= counts[')'] and  # (annotation)
                line[found + 1] != '='  # assignment expression
        ):
            lambda_kw = LAMBDA_REGEX.search(line, 0, found)
            if lambda_kw:
                before = line[:lambda_kw.start()].rstrip()
                if before[-1:] == '=' and before[:-1].strip().isidentifier():
                    yield 0, ("E731 do not assign a lambda expression, use a "
                              "def")
                break
            if STARTSWITH_DEF_REGEX.match(line):
                yield 0, "E704 multiple statements on one line (def)"
            elif STARTSWITH_INDENT_STATEMENT_REGEX.match(line):
                yield found, "E701 multiple statements on one line (colon)"
        prev_found = found
        found = line.find(':', found + 1)
    found = line.find(';')
    while -1 < found:
        if found < last_char:
            yield found, "E702 multiple statements on one line (semicolon)"
        else:
            yield found, "E703 statement ends with a semicolon"
        found = line.find(';', found + 1)


@register_check
def explicit_line_join(logical_line, tokens):
    r"""Avoid explicit line join between brackets.

    The preferred way of wrapping long lines is by using Python's
    implied line continuation inside parentheses, brackets and braces.
    Long lines can be broken over multiple lines by wrapping expressions
    in parentheses.  These should be used in preference to using a
    backslash for line continuation.

    E502: aaa = [123, \\n       123]
    E502: aaa = ("bbb " \\n       "ccc")

    Okay: aaa = [123,\n       123]
    Okay: aaa = ("bbb "\n       "ccc")
    Okay: aaa = "bbb " \\n    "ccc"
    Okay: aaa = 123  # \\
    """
    prev_start = prev_end = parens = 0
    comment = False
    backslash = None
    for token_type, text, start, end, line in tokens:
        if token_type == tokenize.COMMENT:
            comment = True
        if start[0] != prev_start and parens and backslash and not comment:
            yield backslash, "E502 the backslash is redundant between brackets"
        if start[0] != prev_start:
            comment = False  # Reset comment flag on newline
        if end[0] != prev_end:
            if line.rstrip('\r\n').endswith('\\'):
                backslash = (end[0], len(line.splitlines()[-1]) - 1)
            else:
                backslash = None
            prev_start = prev_end = end[0]
        else:
            prev_start = start[0]
        if token_type == tokenize.OP:
            if text in '([{':
                parens += 1
            elif text in ')]}':
                parens -= 1


# The % character is strictly speaking a binary operator, but the
# common usage seems to be to put it next to the format parameters,
# after a line break.
_SYMBOLIC_OPS = frozenset("()[]{},:.;@=%~") | frozenset(("...",))


def _is_binary_operator(token_type, text):
    return (
        token_type == tokenize.OP or
        text in {'and', 'or'}
    ) and (
        text not in _SYMBOLIC_OPS
    )


def _break_around_binary_operators(tokens):
    """Private function to reduce duplication.

    This factors out the shared details between
    :func:`break_before_binary_operator` and
    :func:`break_after_binary_operator`.
    """
    line_break = False
    unary_context = True
    # Previous non-newline token types and text
    previous_token_type = None
    previous_text = None
    for token_type, text, start, end, line in tokens:
        if token_type == tokenize.COMMENT:
            continue
        if ('\n' in text or '\r' in text) and token_type != tokenize.STRING:
            line_break = True
        else:
            yield (token_type, text, previous_token_type, previous_text,
                   line_break, unary_context, start)
            unary_context = text in '([{,;'
            line_break = False
            previous_token_type = token_type
            previous_text = text


@register_check
def break_before_binary_operator(logical_line, tokens):
    r"""
    Avoid breaks before binary oper