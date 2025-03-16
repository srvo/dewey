"""
A drop-in replacement for `argparse` that allows options to also be set via config files and/or environment variables.

:see: `configargparse.ArgumentParser`, `configargparse.add_argument`
"""
import argparse
import ast
import csv
import functools
import json
import glob
import os
import re
import sys
import types
from collections import OrderedDict
import textwrap

if sys.version_info >= (3, 0):
    from io import StringIO
else:
    from StringIO import StringIO


ACTION_TYPES_THAT_DONT_NEED_A_VALUE = [argparse._StoreTrueAction,
    argparse._StoreFalseAction, argparse._CountAction,
    argparse._StoreConstAction, argparse._AppendConstAction]

if sys.version_info >= (3, 9):
    ACTION_TYPES_THAT_DONT_NEED_A_VALUE.append(argparse.BooleanOptionalAction)
    is_boolean_optional_action = lambda action: isinstance(action, argparse.BooleanOptionalAction)
else:
    is_boolean_optional_action = lambda action: False

ACTION_TYPES_THAT_DONT_NEED_A_VALUE = tuple(ACTION_TYPES_THAT_DONT_NEED_A_VALUE)


# global ArgumentParser instances
_parsers = {}

def init_argument_parser(name=None, **kwargs):
    """Creates a global ArgumentParser instance with the given name,
    passing any args other than "name" to the ArgumentParser constructor.
    This instance can then be retrieved using get_argument_parser(..)
    """

    if name is None:
        name = "default"

    if name in _parsers:
        raise ValueError(("kwargs besides 'name' can only be passed in the"
            " first time. '%s' ArgumentParser already exists: %s") % (
            name, _parsers[name]))

    kwargs.setdefault('formatter_class', argparse.ArgumentDefaultsHelpFormatter)
    kwargs.setdefault('conflict_handler', 'resolve')
    _parsers[name] = ArgumentParser(**kwargs)


def get_argument_parser(name=None, **kwargs):
    """Returns the global ArgumentParser instance with the given name. The 1st
    time this function is called, a new ArgumentParser instance will be created
    for the given name, and any args other than "name" will be passed on to the
    ArgumentParser constructor.
    """
    if name is None:
        name = "default"

    if len(kwargs) > 0 or name not in _parsers:
        init_argument_parser(name, **kwargs)

    return _parsers[name]


class ArgumentDefaultsRawHelpFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawTextHelpFormatter,
    argparse.RawDescriptionHelpFormatter):
    """HelpFormatter that adds default values AND doesn't do line-wrapping"""
    pass


class ConfigFileParser(object):
    """This abstract class can be extended to add support for new config file
    formats"""

    def get_syntax_description(self):
        """Returns a string describing the config file syntax."""
        raise NotImplementedError("get_syntax_description(..) not implemented")

    def parse(self, stream):
        """Parses the keys and values from a config file.

        NOTE: For keys that were specified to configargparse as
        action="store_true" or "store_false", the config file value must be
        one of: "yes", "no", "on", "off", "true", "false". Otherwise an error will be raised.

        Args:
            stream (IO): A config file input stream (such as an open file object).

        Returns:
            OrderedDict: Items where the keys are strings and the
            values are either strings or lists (eg. to support config file
            formats like YAML which allow lists).
        """
        raise NotImplementedError("parse(..) not implemented")

    def serialize(self, items):
        """Does the inverse of config parsing by taking parsed values and
        converting them back to a string representing config file contents.

        Args:
            items: an OrderedDict of items to be converted to the config file
                format. Keys should be strings, and values should be either strings
                or lists.

        Returns:
            Contents of config file as a string
        """
        raise NotImplementedError("serialize(..) not implemented")


class ConfigFileParserException(Exception):
    """Raised when config file parsing failed."""


class DefaultConfigFileParser(ConfigFileParser):
    """
    Based on a simplified subset of INI and YAML formats. Here is the
    supported syntax

    .. code::

        # this is a comment
        ; this is also a comment (.ini style)
        ---            # lines that start with --- are ignored (yaml style)
        -------------------
        [section]      # .ini-style section names are treated as comments

        # how to specify a key-value pair (all of these are equivalent):
        name value     # key is case sensitive: "Name" isn't "name"
        name = value   # (.ini style)  (white space is ignored, so name = value same as name=value)
        name: value    # (yaml style)
        --name value   # (argparse style)

        # how to set a flag arg (eg. arg which has action="store_true")
        --name
        name
        name = True    # "True" and "true" are the same

        # how to specify a list arg (eg. arg which has action="append")
        fruit = [apple, orange, lemon]
        indexes = [1, 12, 35 , 40]

    """

    def get_syntax_description(self):
        msg = ("Config file syntax allows: key=value, flag=true, stuff=[a,b,c] "
               "(for details, see syntax at https://goo.gl/R74nmi).")
        return msg

    def parse(self, stream):
       # see ConfigFileParser.parse docstring

        items = OrderedDict()
        for i, line in enumerate(stream):
            line = line.strip()
            if not line or line[0] in ["#", ";", "["] or line.startswith("---"):
                continue

            match = re.match(r'^(?P<key>[^:=;#\s]+)\s*'
                             r'(?:(?P<equal>[:=\s])\s*([\'"]?)(?P<value>.+?)?\3)?'
                             r'\s*(?:\s[;#]\s*(?P<comment>.*?)\s*)?$', line)
            if match:
                key = match.group("key")
                equal = match.group('equal')
                value = match.group("value")
                comment = match.group("comment")
                if value is None and equal is not None and equal != ' ':
                    value = ''
                elif value is None:
                    value = "true"
                if value.startswith("[") and value.endswith("]"):
                    # handle special case of k=[1,2,3] or other json-like syntax
                    try:
                        value = json.loads(value)
                    except Exception as e:
                        # for backward compatibility with legacy format (eg. where config value is [a, b, c] instead of proper json ["a", "b", "c"]
                        value = [elem.strip() for elem in value[1:-1].split(",")]
                if comment:
                    comment = comment.strip()[1:].strip()
                items[key] = value
            else:
                raise ConfigFileParserException("Unexpected line {} in {}: {}".format(i,
                    getattr(stream, 'name', 'stream'), line))
        return items

    def serialize(self, items):
        # see ConfigFileParser.serialize docstring
        r = StringIO()
        for key, value in items.items():
            if isinstance(value, list):
                # handle special case of lists
                value = "["+", ".join(map(str, value))+"]"
            r.write("{} = {}\n".format(key, value))
        return r.getvalue()


class ConfigparserConfigFileParser(ConfigFileParser):
    """parses INI files using pythons configparser."""

    def get_syntax_description(self):
        msg = """Uses configparser module to parse an INI file which allows multi-line
        values.

        Allowed syntax is that for a ConfigParser with the following options:

            allow_no_value = False,
            inline_comment_prefixes = ("#",)
            strict = True
            empty_lines_in_values = False

        See https://docs.python.org/3/library/configparser.html for details.

        Note: INI file sections names are still treated as comments.
        """
        return msg

    def parse(self, stream):
        # see ConfigFileParser.parse docstring
        import configparser
        from ast import literal_eval
        # parse with configparser to allow multi-line values
        config = configparser.ConfigParser(
            delimiters=("=",":"),
            allow_no_value=False,
            comment_prefixes=("#",";"),
            inline_comment_prefixes=("#",";"),
            strict=True,
            empty_lines_in_values=False,
        )
        try:
            config.read_string(stream.read())
        except Exception as e:
            raise ConfigFileParserException("Couldn't parse config file: %s" % e)

        # convert to dict and remove INI section names
        result = OrderedDict()
        for section in config.sections():
            for k,v in config[section].items():
                multiLine2SingleLine = v.replace('\n',' ').replace('\r',' ')
                # handle special case for lists
                if '[' in multiLine2SingleLine and ']' in multiLine2SingleLine:
                    # ensure not a dict with a list value
                    prelist_string = multiLine2SingleLine.split('[')[0]
                    if '{' not in prelist_string:
                        result[k] = literal_eval(multiLine2SingleLine)
                    else:
                        result[k] = multiLine2SingleLine
                else:
                    result[k] = multiLine2SingleLine
        return result

    def serialize(self, items):
        # see ConfigFileParser.serialize docstring
        import configparser
        import io
        config = configparser.ConfigParser(
            allow_no_value=False,
            inline_comment_prefixes=("#",),
            strict=True,
            empty_lines_in_values=False,
        )
        items = {"DEFAULT": items}
        config.read_dict(items)
        stream = io.StringIO()
        config.write(stream)
        stream.seek(0)
        return stream.read()


class YAMLConfigFileParser(ConfigFileParser):
    """Parses YAML config files. Depends on the PyYAML module.
    https://pypi.python.org/pypi/PyYAML
    """

    def get_syntax_description(self):
        msg = ("The config file uses YAML syntax and must represent a YAML "
            "'mapping' (for details, see http://learn.getgrav.org/advanced/yaml).")
        return msg

    def _load_yaml(self):
        """lazy-import PyYAML so that configargparse doesn't have to depend
        on it unless this parser is used."""
        try:
            import yaml
        except ImportError:
            raise ConfigFileParserException("Could not import yaml. "
                "It can be installed by running 'pip install PyYAML'")

        try:
            from yaml import CSafeLoader as SafeLoader
            from yaml import CDumper as Dumper
        except ImportError:
            from yaml import SafeLoader
            from yaml import Dumper

        return yaml, SafeLoader, Dumper

    def parse(self, stream):
        # see ConfigFileParser.parse docstring
        yaml, SafeLoader, _ = self._load_yaml()

        try:
            parsed_obj = yaml.load(stream, Loader=SafeLoader)
        except Exception as e:
            raise ConfigFileParserException("Couldn't parse config file: %s" % e)

        if not isinstance(parsed_obj, dict):
            raise ConfigFileParserException("The config file doesn't appear to "
                "contain 'key: value' pairs (aka. a YAML mapping). "
                "yaml.load('%s') returned type '%s' instead of 'dict'." % (
                getattr(stream, 'name', 'stream'),  type(parsed_obj).__name__))

        result = OrderedDict()
        for key, value in parsed_obj.items():
            if isinstance(value, list):
                result[key] = value
            elif value is None:
                pass
            else:
                result[key] = str(value)

        return result

    def serialize(self, items, default_flow_style=False):
        # see ConfigFileParser.serialize docstring

        # lazy-import so there's no dependency on yaml unless this class is used
        yaml, _, Dumper = self._load_yaml()

        # it looks like ordering can't be preserved: http://pyyaml.org/ticket/29
        items = dict(items)
        return yaml.dump(items, default_flow_style=default_flow_style, Dumper=Dumper)


"""
Provides `configargparse.ConfigFileParser` classes to parse ``TOML`` and ``INI`` files with **mandatory** support for sections.
Useful to integrate configuration into project files like ``pyproject.toml`` or ``setup.cfg``.

`TomlConfigParser` usage:

>>> TomlParser = TomlConfigParser(['tool.my_super_tool']) # Simple TOML parser.
>>> parser = ArgumentParser(..., default_config_files=['./pyproject.toml'], config_file_parser_class=TomlParser)

`IniConfigParser` works the same way (also it optionaly convert multiline strings to list with argument ``split_ml_text_to_list``).

`CompositeConfigParser` usage:

>>> MY_CONFIG_SECTIONS = ['tool.my_super_tool', 'tool:my_super_tool', 'my_super_tool']
>>> TomlParser =  TomlConfigParser(MY_CONFIG_SECTIONS)
>>> IniParser = IniConfigParser(MY_CONFIG_SECTIONS, split_ml_text_to_list=True)
>>> MixedParser = CompositeConfigParser([TomlParser, IniParser]) # This parser supports both TOML and INI formats.
>>> parser = ArgumentParser(..., default_config_files=['./pyproject.toml', 'setup.cfg', 'my_super_tool.ini'], config_file_parser_class=MixedParser)

"""

# I did not invented these regex, just put together some stuff from:
# - https://stackoverflow.com/questions/11859442/how-to-match-string-in-quotes-using-regex
# - and https://stackoverflow.com/a/41005190

_QUOTED_STR_REGEX = re.compile(r'(^\"(?:\\.|[^\"\\])*\"$)|'
                               r'(^\'(?:\\.|[^\'\\])*\'$)')

_TRIPLE_QUOTED_STR_REGEX = re.compile(r'(^\"\"\"(\s+)?(([^\"]|\"([^\"]|\"[^\"]))*(\"\"?)?)?(\s+)?(?:\\.|[^\"\\])?\"\"\"$)|'
                                                                                                 # Unescaped quotes at the end of a string generates
                                                                                                 # "SyntaxError: EOL while scanning string literal",
                                                                                                 # so we don't account for those kind of strings as quoted.
                                      r'(^\'\'\'(\s+)?(([^\']|\'([^\']|\'[^\']))*(\'\'?)?)?(\s+)?(?:\\.|[^\'\\])?\'\'\'$)', flags=re.DOTALL)

@functools.lru_cache(maxsize=256, typed=True)
def is_quoted(text, triple=True):
    """
    Detect whether a string is a quoted representation.

    :param triple: Also match tripple quoted strings.
    """
    return bool(_QUOTED_STR_REGEX.match(text)) or \
        (triple and bool(_TRIPLE_QUOTED_STR_REGEX.match(text)))

def unquote_str(text, triple=True):
    """
    Unquote a maybe quoted string representation.
    If the string is not detected as being a quoted representation, it returns the same string as passed.
    It supports all kinds of python quotes: ``\"\"\"``, ``'''``, ``"`` and ``'``.

    :param triple: Also unquote tripple quoted strings.
    @raises ValueError: If the string is detected as beeing quoted but literal_eval() fails to evaluate it as string.
        This would be a bug in the regex.
    """
    if is_quoted(text, triple=triple):
        try:
            s = ast.literal_eval(text)
            assert isinstance(s, str)
        except Exception as e:
            raise ValueError(f"Error trying to unquote the quoted string: {text}: {e}") from e
        return s
    return text

def parse_toml_section_name(section_name):
    """
    Parse a TOML section name to a sequence of strings.

    The following names are all valid:

    .. python::

        "a.b.c"            # this is best practice -> returns ("a", "b", "c")
        " d.e.f "          # same as [d.e.f] -> returns ("d", "e", "f")
        " g .  h  . i "    # same as [g.h.i] -> returns ("g", "h", "i")
        ' j . "ʞ" . "l" '  # same as [j."ʞ"."l"], double or simple quotes here are supported. -> returns ("j", "ʞ", "l")
    """
    section = []
    for row in csv.reader([section_name], delimiter='.'):
        for a in row:
            section.append(unquote_str(a.strip(), triple=False))
    return tuple(section)

def get_toml_section(data, section):
    """
    Given some TOML data (as loaded with `toml.load()`), returns the requested section of the data.
    Returns ``None`` if the section is not found.
    """
    sections = parse_toml_section_name(section) if isinstance(section, str) else section
    itemdata = data.get(sections[0])
    if not itemdata:
        return None
    sections = sections[1:]
    if sections:
        return get_toml_section(itemdata, sections)
    else:
        if not isinstance(itemdata, dict):
            return None
        return itemdata

class TomlConfigParser(ConfigFileParser):
    """
    Create a TOML parser bounded to the list of provided sections.

    Example::
        # this is a comment
        [tool.my-software] # TOML section table.
        # how to specify a key-value pair
        format-string = "restructuredtext" # strings must be quoted
        # how to set an arg which has action="store_true"
        warnings-as-errors = true
        # how to set an arg which has action="count" or type=int
        verbosity = 1
        # how to specify a list arg (eg. arg which has action="append")
        repeatable-option = ["https://docs.python.org/3/objects.inv",
                       "https://twistedmatrix.com/documents/current/api/objects.inv"]
        # how to specify a multiline text:
        multi-line-text = '''
            Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Vivamus tortor odio, dignissim non ornare non, laoreet quis nunc.
            Maecenas quis dapibus leo, a pellentesque leo.
            '''

    Note that the config file fragment above is also valid for the `IniConfigParser` class and would be parsed the same manner.
    Thought, any valid TOML config file will not be necessarly parsable with `IniConfigParser` (INI files must be rigorously indented whereas TOML files).

    See the `TOML specification <>`_ for details.
    """

    def __init__(self, sections):
        """
        :param sections: The section names bounded to the new parser.
        """
        super().__init__()
        self.sections = sections

    def __call__(self):
        return self

    def parse(self, stream):
        """Parses the keys and values from a TOML config file."""
        # parse with configparser to allow multi-line values
        import toml
        try:
            config = toml.load(stream)
        except Exception as e:
            raise ConfigFileParserException("Couldn't parse TOML file: %s" % e)

        # convert to dict and filter based on section names
        result = OrderedDict()

        for section in self.sections:
            data = get_toml_section(config, section)
            if data:
                # Seems a little weird, but anything that is not a list is converted to string,
                # It will be converted back to boolean, int or whatever after.
                # Because config values are still passed to argparser for computation.
                for key, value in data.items():
                    if isinstance(value, list):
                        result[key] = value
                    elif value is None:
                        pass
                    else:
                        result[key] = str(value)
                break

        return result

    def get_syntax_description(self):
        return ("Config file syntax is Tom's Obvious, Minimal Language. "
                "See https://github.com/toml-lang/toml/blob/v0.5.0/README.md for details.")

class IniConfigParser(ConfigFileParser):
    """
    Create a INI parser bounded to the list of provided sections.
    Optionaly convert multiline strings to list.

    Example (if split_ml_text_to_list=False)::

        # this is a comment
        ; also a comment
        [my-software]
        # how to specify a key-value pair
        format-string: restructuredtext
        # white space are ignored, so name = value same as name=value
        # this is why you can quote strings
        quoted-string = '\thello\tmom...  '
        # how to set an arg which has action="store_true"
        warnings-as-errors = true
        # how to set an arg which has action="count" or type=int
        verbosity = 1
        # how to specify a list arg (eg. arg which has action="append")
        repeatable-option = ["https://docs.python.org/3/objects.inv",
                       "https://twistedmatrix.com/documents/current/api/objects.inv"]
        # how to specify a multiline text:
        multi-line-text =
            Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Vivamus tortor odio, dignissim non ornare non, laoreet quis nunc.
            Maecenas quis dapibus leo, a pellentesque leo.

    Example (if split_ml_text_to_list=True)::

        # the same rules are applicable with the following changes:
        [my-software]
        # how to specify a list arg (eg. arg which has action="append")
        repeatable-option = # Just enter one value per line (the list literal format can also be used)
            https://docs.python.org/3/objects.inv
            https://twistedmatrix.com/documents/current/api/objects.inv
        # how to specify a multiline text (you have to quote it):
        multi-line-text = '''
            Lorem ipsum dolor sit amet, consectetur adipiscing elit.
            Vivamus tortor odio, dignissim non ornare non, laoreet quis nunc.
            Maecenas quis dapibus leo, a pellentesque leo.
            '''
    """

    def __init__(self, sections, split_ml_text_to_list):
        """
        :param sections: The section names bounded to the new parser.
        :split_ml_text_to_list: Wether to convert multiline strings to list
        """
        super().__init__()
        self.sections = sections
        self.split_ml_text_to_list = split_ml_text_to_list

    def __call__(self):
        return self

    def parse(self, stream):
        """Parses the keys and values from an INI config file."""
        # parse with configparser to allow multi-line values
        import configparser
        config = configparser.ConfigParser()
        try:
            config.read_string(stream.read())
        except Exception as e:
            raise ConfigFileParserException("Couldn't parse INI file: %s" % e)

        # convert to dict and filter based on INI section names
        result = OrderedDict()
        for section in config.sections() + [configparser.DEFAULTSECT]:
            if section not in self.sections:
                continue
            for k,v in config[section].items():
                strip_v = v.strip()
                if not strip_v:
                    # ignores empty values, anyway allow_no_value=False by default so this should not happend.
                    continue
                # evaluate lists
                if strip_v.startswith('[') and strip_v.endswith(']'):
                    try:
                        result[k] = ast.literal_eval(strip_v)
                    except ValueError as e:
                        # error evaluating object
                        raise ConfigFileParserException("Error evaluating list: " + str(e) + ". Put quotes around your text if it's meant to be a string.") from e
                else:
                    if is_quoted(strip_v):
                        # evaluate quoted string
                        try:
                            result[k] = unquote_str(strip_v)
                        except ValueError as e:
                            # error unquoting string
                            raise ConfigFileParserException(str(e)) from e
                    # split multi-line text into list of strings if split_ml_text_to_list is enabled.
                    elif self.split_ml_text_to_list and '\n' in v.rstrip('\n'):
                        try:
                            result[k] = [unquote_str(i) for i in strip_v.split('\n') if i]
                        except ValueError as e:
                            # error unquoting string
                            raise ConfigFileParserException(str(e)) from e
                    else:
                        result[k] = v
        return result

    def get_syntax_description(self):
        msg = ("Uses configparser module to parse an INI file which allows multi-line values. "
                "See https://docs.python.org/3/library/configparser.html for details. "
                "This parser includes support for quoting strings literal as well as python list syntax evaluation. ")
        if self.split_ml_text_to_list:
            msg += ("Alternatively lists can be constructed with a plain multiline string, "
                "each non-empty line will be converted to a list item.")
        return msg

class CompositeConfigParser(ConfigFileParser):
    """
    Createa a config parser composed by others `ConfigFileParser`s.

    The composite parser will successively try to parse the file with each parser,
    until it succeeds, else raise execption with all encountered errors.
    """

    def __init__(self, config_parser_types):
        super().__init__()
        self.parsers = [p() for p in config_parser_types]

    def __call__(self):
        return self

    def parse(self, stream):
        errors = []
        for p in self.parsers:
            try:
                return p.parse(stream) # type: ignore[no-any-return]
            except Exception as e:
                stream.seek(0)
                errors.append(e)
        raise ConfigFileParserException(
                f"Error parsing config: {', '.join(repr(str(e)) for e in errors)}")

    def get_syntax_description(self) :
        def guess_format_name(classname):
            strip = classname.lower().strip('_').replace('parser',
                '').replace('config', '').replace('file', '')
            return strip.upper() if strip else '??'

        msg = "Uses multiple config parser settings (in order): \n"
        for i, parser in enumerate(self.parsers):
            msg += f"[{i+1}] {guess_format_name(parser.__class__.__name__)}: {parser.get_syntax_description()} \n"
        return msg

# used while parsing args to keep track of where they came from
_COMMAND_LINE_SOURCE_KEY = "command_line"
_ENV_VAR_SOURCE_KEY = "environment_variables"
_CONFIG_FILE_SOURCE_KEY = "config_file"
_DEFAULTS_SOURCE_KEY = "defaults"


class ArgumentParser(argparse.ArgumentParser):
    """Drop-in replacement for `argparse.ArgumentParser` that adds support for
    environment variables and ``.ini`` or ``.yaml-style`` config files.
    """

    def __init__(self, *args, **kwargs):

        r"""Supports args of the `argparse.ArgumentParser` constructor
        as \*\*kwargs, as well as the following additional args.

        Arguments:
            add_config_file_help: Whether to add a description of config file
                syntax to the help message.
            add_env_var_help: Whether to add something to the help message for
                args that can be set through environment variables.
            auto_env_var_prefix: If set to a string instead of None, all config-
                file-settable options will become also settable via environment
                variables whose names are this prefix followed by the config
                file key, all in upper case. (eg. setting this to ``foo_`` will
                allow an arg like ``--my-arg`` to also be set via the FOO_MY_ARG
                environment variable)
            default_config_files: When specified, this list of config files will
                be parsed in order, with the values from each config file
                taking precedence over previous ones. This allows an application
                to look for config files in multiple standard locations such as
                the install directory, home directory, and current directory.
                Also, shell \* syntax can be used to specify all conf files in a
                directory. For example::

                    ["/etc/conf/app_config.ini",
                    "/etc/conf/conf-enabled/*.ini",
                    "~/.my_app_config.ini",
                    "./app_config.txt"]

            ignore_unknown_config_file_keys: If true, settings that are found
                in a config file but don't correspond to any defined
                configargparse args will be ignored. If false, they will be
                processed and appended to the commandline like other args, and
                can be retrieved using parse_known_args() instead of parse_args()
            config_file_open_func: function used to open a config file for reading
                or writing. Needs to return a file-like object.
            config_file_parser_class: configargparse.ConfigFileParser subclass
                which determines the config file format. configargparse comes
                with DefaultConfigFileParser and YAMLConfigFileParser.
            args_for_setting_config_path: A list of one or more command line
                args to be used for specifying the config file path
                (eg. ["-c", "--config-file"]). Default: []
            config_arg_is_required: When args_for_setting_config_path is set,
                set this to True to always require users to provide a config path.
            config_arg_help_message: the help message to use for the
                args listed in args_for_setting_config_path.
            args_for_writing_out_config_file: A list of one or more command line
                args to use for specifying a config file output path. If
                provided, these args cause configargparse to write out a config
                file with settings based on the other provided commandline args,
                environment variants and defaults, and then to exit.
                (eg. ["-w", "--write-out-config-file"]). Default: []
            write_out_config_file_arg_help_message: The help message to use for
                the args in args_for_writing_out_config_file.
        """
        # This is the only way to make positional args (tested in the argparse
        # main test suite) and keyword arguments work across both Python 2 and
        # 3. This could be refactored to not need extra local variables.
        add_config_file_help = kwargs.pop('add_config_file_help', True)
        add_env_var_help = kwargs.pop('add_env_var_help', True)
        auto_env_var_prefix = kwargs.pop('auto_env_var_prefix', None)
        default_config_files = kwargs.pop('default_config_files', [])
        ignore_unknown_config_file_keys = kwargs.pop(
            'ignore_unknown_config_file_keys', False)
        config_file_parser_class = kwargs.pop('config_file_parser_class',
                                              DefaultConfigFileParser)
        args_for_setting_config_path = kwargs.pop(
            'args_for_setting_config_path', [])
        config_arg_is_required = kwargs.pop('config_arg_is_required', False)
        config_arg_help_message = kwargs.pop('config_arg_help_message',
                                             "config file path")
        args_for_writing_out_config_file = kwargs.pop(
            'args_for_writing_out_config_file', [])
        write_out_config_file_arg_help_message = kwargs.pop(
            'write_out_config_file_arg_help_message', "takes the current "
            "command line args and writes them out to a config file at the "
            "given path, then exits")

        self._config_file_open_func = kwargs.pop('config_file_open_func', open)

        self._add_config_file_help = add_config_file_help
        self._add_env_var_help = add_env_var_help
        self._auto_env_var_prefix = auto_env_var_prefix

        argparse.ArgumentParser.__init__(self, *args, **kwargs)

        # parse the additional args
        if config_file_parser_class is None:
            self._config_file_parser = DefaultConfigFileParser()
        else:
            self._config_file_parser = config_file_parser_class()

        self._default_config_files = default_config_files
        self._ignore_unknown_config_file_keys = ignore_unknown_config_file_keys
        if args_for_setting_config_path:
            self.add_argument(*args_for_setting_config_path, dest="config_file",
                required=config_arg_is_required, help=config_arg_help_message,
                is_config_file_arg=True)

        if args_for_writing_out_config_file:
            self.add_argument(*args_for_writing_out_config_file,
                dest="write_out_config_file_to_this_path",
                metavar="CONFIG_OUTPUT_PATH",
                help=write_out_config_file_arg_help_message,
                is_write_out_config_file_arg=True)

    def parse_args(self, args = None, namespace = None,
                   config_file_contents = None, env_vars = os.environ):
        """Supports all the same args as the `argparse.ArgumentParser.parse_args()`,
        as well as the following additional args.

        Arguments:
            args: a list of args as in argparse, or a string (eg. "-x -y bla")
            config_file_contents: String. Used for testing.
            env_vars: Dictionary. Used for testing.

        Returns:
            argparse.Namespace: namespace
        """
        args, argv = self.parse_known_args(
            args=args,
            namespace=namespace,
            config_file_contents=config_file_contents,
            env_vars=env_vars,
            ignore_help_args=False)

        if argv:
            self.error('unrecognized arguments: %s' % ' '.join(argv))
        return args

    def parse_known_args(
            self,
            args=None,
            namespace=None,
            config_file_contents=None,
            env_vars=os.environ,
            ignore_help_args=False,
    ):
        """Supports all the same args as the `argparse.ArgumentParser.parse_args()`,
        as well as the following additional args.

        Arguments:
            args: a list of args as in argparse, or a string (eg. "-x -y bla")
            config_file_contents (str). Used for testing.
            env_vars (dict). Used for testing.
            ignore_help_args (bool): This flag determines behavior when user specifies ``--help`` or ``-h``. If False,
                it will have the default behavior - printing help and exiting. If True, it won't do either.

        Returns:
            tuple[argparse.Namespace, list[str]]: tuple namescpace, unknown_args
        """
        if args is None:
            args = sys.argv[1:]
        elif isinstance(args, str):
            args = args.split()
        else:
            args = list(args)

        for a in self._actions:
            a.is_positional_arg = not a.option_strings

        if ignore_help_args:
            args = [arg for arg in args if arg not in ("-h", "--help")]

        # maps a string describing the source (eg. env var) to a settings dict
        # to keep track of where values came from (used by print_values()).
        # The settings dicts for env vars and config files will then map
        # the config key to an (argparse Action obj, string value) 2-tuple.
        self._source_to_settings = OrderedDict()
        if args:
            a_v_pair = (None, list(args))  # copy args list to isolate changes
            self._source_to_settings[_COMMAND_LINE_SOURCE_KEY] = {'': a_v_pair}

        # handle auto_env_var_prefix __init__ arg by setting a.env_var as needed
        if self._auto_env_var_prefix is not None:
            for a in self._actions:
                config_file_keys = self.get_possible_config_keys(a)
                if config_file_keys and not (a.env_var or a.is_positional_arg
                    or a.is_config_file_arg or a.is_write_out_config_file_arg or
                    isinstance(a, argparse._VersionAction) or
                    isinstance(a, argparse._HelpAction)):
                    stripped_config_file_key = config_file_keys[0].strip(
                        self.prefix_chars)
                    a.env_var = (self._auto_env_var_prefix +
                                 stripped_config_file_key).replace('-', '_').upper()

        # add env var settings to the commandline that aren't there already
        env_var_args = []
        nargs = False
        actions_with_env_var_values = [a for a in self._actions
            if not a.is_positional_arg and a.env_var and a.env_var in env_vars
                and not already_on_command_line(args, a.option_strings, self.prefix_chars)]
        for action in actions_with_env_var_values:
            key = action.env_var
            value = env_vars[key]
            # Make list-string into list.
            if action.nargs or isinstance(action, argparse._AppendAction):
                nargs = True
                if value.startswith("[") and value.endswith("]"):
                    # handle special case of k=[1,2,3] or other json-like syntax
                    try:
                        value = json.loads(value)
                    except Exception:
                        # for backward compatibility with legacy format (eg. where config value is [a, b, c] instead of proper json ["a", "b", "c"]
                        value = [elem.strip() for elem in value[1:-1].split(",")]
            env_var_args += self.convert_item_to_command_line_arg(
                action, key, value)

        if nargs:
            args = args + env_var_args
        else:
            args = env_var_args + args

        if env_var_args:
            self._source_to_settings[_ENV_VAR_SOURCE_KEY] = OrderedDict(
                [(a.env_var, (a, env_vars[a.env_var]))
                    for a in actions_with_env_var_values])

        # before parsing any config files, check if -h was specified.
        supports_help_arg = any(
            a for a in self._actions if isinstance(a, argparse._HelpAction))
        skip_config_file_parsing = supports_help_arg and (
            "-h" in args or "--help" in args)

        # prepare for reading config file(s)
        known_config_keys = {config_key: action for action in self._actions
            for config_key in self.get_possible_config_keys(action)}

        # open the config file(s)
        config_streams = []
        if config_file_contents is not None:
            stream = StringIO(config_file_contents)
            stream.name = "method arg"
            config_streams = [stream]
        elif not skip_config_file_parsing:
            config_streams = self._open_config_files(args)

        # parse each config file
        for stream in reversed(config_streams):
            try:
                config_items = self._config_file_parser.parse(stream)
            except ConfigFileParserException as e:
                self.error(str(e))
            finally:
                if hasattr(stream, "close"):
                    stream.close()

            # add each config item to the commandline unless it's there already
            config_args = []
            nargs = False
            for key, value in config_items.items():
                if key in known_config_keys:
                    action = known_config_keys[key]
                    discard_this_key = already_on_command_line(
                        args, action.option_strings, self.prefix_chars)
                else:
                    action = None
                    discard_this_key = self._ignore_unknown_config_file_keys or \
                        already_on_command_line(
                            args,
                            [self.get_command_line_key_for_unknown_config_file_setting(key)],
                            self.prefix_chars)

                if not discard_this_key:
                    config_args += self.convert_item_to_command_line_arg(
                        action, key, value)
                    source_key = "%s|%s" %(_CONFIG_FILE_SOURCE_KEY, stream.name)
                    if source_key not in self._source_to_settings:
                        self._source_to_settings[source_key] = OrderedDict()
                    self._source_to_settings[source_key][key] = (action, value)
                    if (action and action.nargs or
                        isinstance(action, argparse._AppendAction)):
                        nargs = True

            if nargs:
                args = args + config_args
            else:
                args = config_args + args

        # save default settings for use by print_values()
        default_settings = OrderedDict()
        for action in self._actions:
            cares_about_default_value = (not action.is_positional_arg or
                action.nargs in [OPTIONAL, ZERO_OR_MORE])
            if (already_on_command_line(args, action.option_strings, self.prefix_chars) or
                    not cares_about_default_value or
                    action.default is None or
                    action.default == SUPPRESS or
                    isinstance(action, ACTION_TYPES_THAT_DONT_NEED_A_VALUE)):
                continue
            else:
                if action.option_strings:
                    key = action.option_strings[-1]
                else:
                    key = action.dest
                default_settings[key] = (action, str(action.default))

        if default_settings:
            self._source_to_settings[_DEFAULTS_SOURCE_KEY] = default_settings

        # parse all args (including commandline, config file, and env var)
        namespace, unknown_args = argparse.ArgumentParser.parse_known_args(
            self, args=args, namespace=namespace)
        # handle any args that have is_write_out_config_file_arg set to true
        # check if the user specified this arg on the commandline
        output_file_paths = [getattr(namespace, a.dest, None) for a in self._actions
                             if getattr(a, "is_write_out_config_file_arg", False)]
        output_file_paths = [a for a in output_file_paths if a is not None]
        self.write_config_file(namespace, output_file_paths, exit_after=True)
        return namespace, unknown_args

    def get_source_to_settings_dict(self):
        """
        If called after `parse_args()` or `parse_known_args()`, returns a dict that contains up to 4 keys corresponding
        to where a given option's value is coming from:
        - "command_line"
        - "environment_variables"
        - "config_file"
        - "defaults"
        Each such key, will be mapped to another dictionary containing the options set via that method. Here the key
        will be the option name, and the value will be a 2-tuple of the form (`argparse.Action` obj, `str` value).

        Returns:
            dict[str, dict[str, tuple[argparse.Action, str]]]: source to settings dict
        """
        # _source_to_settings is set in parse_know_args().
        return self._source_to_settings # type:ignore[attribute-error]


    def write_config_file(self, parsed_namespace, output_file_paths, exit_after=False):
        """Write the given settings to output files.

        Args:
            parsed_namespace: namespace object created within parse_known_args()
            output_file_paths: any number of file paths to write the config to
            exit_after: whether to exit the program after writing the config files
        """
        for output_file_path in output_file_paths:
            # validate the output file path
            try:
                with self._config_file_open_func(output_file_path, "w") as output_file:
                    pass
            except IOError as e:
                raise ValueError("Couldn't open {} for writing: {}".format(
                    output_file_path, e))
        if output_file_paths:
            # generate the config file contents
            config_items = self.get_items_for_config_file_output(
                self._source_to_settings, parsed_namespace)
            file_contents = self._config_file_parser.serialize(config_items)
            for output_file_path in output_file_paths:
                with self._config_file_open_func(output_file_path, "w") as output_file:
                    output_file.write(file_contents)

            print("Wrote config file to " + ", ".join(output_file_paths))
            if exit_after:
                self.exit(0)

    def get_command_line_key_for_unknown_config_file_setting(self, key):
        """Compute a commandline arg key to be used for a config file setting
        that doesn't correspond to any defined configargparse arg (and so
        doesn't have a user-specified commandline arg key).

        Args:
            key: The config file key that was being set.

        Returns:
            str: command line key
        """
        key_without_prefix_chars = key.strip(self.prefix_chars)
        command_line_key = self.prefix_chars[0]*2 + key_without_prefix_chars

        return command_line_key

    def get_items_for_config_file_output(self, source_to_settings,
                                         parsed_namespace):
        """Converts the given settings back to a dictionary that can be passed
        to ConfigFormatParser.serialize(..).

        Args:
            source_to_settings: the dictionary described in parse_known_args()
            parsed_namespace: namespace object created within parse_known_args()
        Returns:
            OrderedDict: where keys are strings and values are either strings
            or lists
        """
        config_file_items = OrderedDict()
        for source, settings in source_to_settings.items():
            if source == _COMMAND_LINE_SOURCE_KEY:
                _, existing_command_line_args = settings['']
                for action in self._actions:
                    config_file_keys = self.get_possible_config_keys(action)
                    if config_file_keys and not action.is_positional_arg and \
                        already_on_command_line(existing_command_line_args,
                                                action.option_strings,
                                                self.prefix_chars):
                        value = getattr(parsed_namespace, action.dest, None)
                        if value is not None:
                            if isinstance(value, bool):
                                value = str(value).lower()
                            config_file_items[config_file_keys[0]] = value

            elif source == _ENV_VAR_SOURCE_KEY:
                for key, (action, value) in settings.items():
                    config_file_keys = self.get_possible_config_keys(action)
                    if config_file_keys:
                        value = getattr(parsed_namespace, action.dest, None)
                        if value is not None:
                            config_file_items[config_file_keys[0]] = value
            elif source.startswith(_CONFIG_FILE_SOURCE_KEY):
                for key, (action, value) in settings.items():
                    config_file_items[key] = value
            elif source == _DEFAULTS_SOURCE_KEY:
                for key, (action, value) in settings.items():
                    config_file_keys = self.get_possible_config_keys(action)
                    if config_file_keys:
                        value = getattr(parsed_namespace, action.dest, None)
                        if value is not None:
                            config_file_items[config_file_keys[0]] = value
        return config_file_items

    def convert_item_to_command_line_arg(self, action, key, value):
        """Converts a config file or env var key + value to a list of
        commandline args to append to the commandline.

        Args:
            action: The argparse Action object for this setting, or None if this
                config file setting doesn't correspond to any defined
                configargparse arg.
            key: string (config file key or env var name)
            value: parsed value of type string or list

        Returns:
            list[str]: args
        """
        args = []

        if action is None:
            command_line_key = \
                self.get_command_line_key_for_unknown_config_file_setting(key)
        else:
            if not is_boolean_optional_action(action):
                command_line_key = action.option_strings[-1]

        # handle boolean value
        if action is not None and isinstance(action, ACTION_TYPES_THAT_DONT_NEED_A_VALUE):
            assert isinstance(value, str), "config parser should convert anything that is not a list to string."
            if value.lower() in ("true", "yes", "on", "1"):
                if not is_boolean_optional_action(action):
                    args.append( command_line_key )
                else:
                    # --foo
                    args.append(action.option_strings[0])
            elif value.lower() in ("false", "no", "off", "0"):
                # don't append when set to "false" / "no"
                if not is_boolean_optional_action(action):
                    pass
                else:
                    # --no-foo
                    args.append(action.option_strings[1])
            elif isinstance(action, argparse._CountAction):
                for arg in args:
                    if any([arg.startswith(s) for s in action.option_strings]):
                        value = 0
                args += [action.option_strings[0]] * int(value)
            else:
                self.error("Unexpected value for %s: '%s'. Expecting 'true', "
                           "'false',
