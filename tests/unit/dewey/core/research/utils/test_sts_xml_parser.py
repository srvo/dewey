import unittest
from unittest.mock import patch, mock_open
import xml.etree.ElementTree as ET
from typing import List, Optional

import pytest

from dewey.core.research.utils.sts_xml_parser import STSXmlParser
from dewey.core.base_script import BaseScript


class TestSTSXmlParser(unittest.TestCase):
    """Unit tests for the STSXmlParser class."""

    def setUp(self):
        """Set up for the tests."""
        self.parser = STSXmlParser()
        self.parser.logger = unittest.mock.MagicMock()  # Mock the logger

    def test_init(self):
        """Test the __init__ method."""
        self.assertEqual(self.parser.config_section, "sts_xml_parser")

    def test_run(self):
        """Test the run method."""
        self.parser.run()
        self.parser.logger.info.assert_called_with("STSXmlParser is running.")

    @patch("dewey.core.research.utils.sts_xml_parser.ET.parse")
    def test_parse_xml_file_success(self, mock_parse):
        """Test parse_xml_file method with a valid XML file."""
        mock_tree = unittest.mock.MagicMock()
        mock_root = unittest.mock.MagicMock()
        mock_tree.getroot.return_value = mock_root
        mock_parse.return_value = mock_tree

        file_path = "test.xml"
        root = self.parser.parse_xml_file(file_path)

        mock_parse.assert_called_once_with(file_path)
        self.assertEqual(root, mock_root)
        self.parser.logger.info.assert_called_with(f"Parsing XML file: {file_path}")
        self.parser.logger.debug.assert_called_with(f"XML file parsed successfully.")

    @patch("dewey.core.research.utils.sts_xml_parser.ET.parse", side_effect=FileNotFoundError)
    def test_parse_xml_file_file_not_found(self, mock_parse):
        """Test parse_xml_file method when the XML file is not found."""
        file_path = "nonexistent.xml"
        with self.assertRaises(FileNotFoundError):
            self.parser.parse_xml_file(file_path)
        self.parser.logger.error.assert_called_with(f"XML file not found: {file_path}")

    @patch("dewey.core.research.utils.sts_xml_parser.ET.parse", side_effect=ET.ParseError("Parse error"))
    def test_parse_xml_file_parse_error(self, mock_parse):
        """Test parse_xml_file method when the XML file has a parsing error."""
        file_path = "invalid.xml"
        with self.assertRaises(ET.ParseError):
            self.parser.parse_xml_file(file_path)
        self.parser.logger.error.assert_called_with(f"Error parsing XML file: {file_path}: Parse error")

    def test_extract_text_from_element_success(self):
        """Test extract_text_from_element method with a valid XPath."""
        root = ET.fromstring("<root><element>text</element></root>")
        xpath = "element"
        text = self.parser.extract_text_from_element(root, xpath)
        self.assertEqual(text, "text")
        self.parser.logger.debug.assert_called_with(f"Extracted text from {xpath}: text")

    def test_extract_text_from_element_element_not_found(self):
        """Test extract_text_from_element method when the element is not found."""
        root = ET.fromstring("<root><element>text</element></root>")
        xpath = "nonexistent"
        text = self.parser.extract_text_from_element(root, xpath)
        self.assertIsNone(text)
        self.parser.logger.warning.assert_called_with(f"Element not found for XPath: {xpath}")

    def test_extract_text_from_element_exception(self):
        """Test extract_text_from_element method when an exception occurs."""
        root = unittest.mock.MagicMock()
        root.find.side_effect = Exception("XPath error")
        xpath = "element"
        text = self.parser.extract_text_from_element(root, xpath)
        self.assertIsNone(text)
        self.parser.logger.error.assert_called_with(f"Error extracting text from XPath {xpath}: XPath error")

    def test_extract_all_texts_from_element_success(self):
        """Test extract_all_texts_from_element method with a valid XPath."""
        root = ET.fromstring("<root><element>text1</element><element>text2</element></root>")
        xpath = "element"
        texts = self.parser.extract_all_texts_from_element(root, xpath)
        self.assertEqual(texts, ["text1", "text2"])
        self.parser.logger.debug.assert_any_call(f"Extracted text from {xpath}: text1")
        self.parser.logger.debug.assert_any_call(f"Extracted text from {xpath}: text2")

    def test_extract_all_texts_from_element_element_not_found(self):
        """Test extract_all_texts_from_element method when the element is not found."""
        root = ET.fromstring("<root><element>text1</element><element>text2</element></root>")
        xpath = "nonexistent"
        texts = self.parser.extract_all_texts_from_element(root, xpath)
        self.assertEqual(texts, [])
        self.parser.logger.warning.assert_called_with(f"Element not found for XPath: {xpath}")

    def test_extract_all_texts_from_element_exception(self):
        """Test extract_all_texts_from_element method when an exception occurs."""
        root = unittest.mock.MagicMock()
        root.findall.side_effect = Exception("XPath error")
        xpath = "element"
        texts = self.parser.extract_all_texts_from_element(root, xpath)
        self.assertEqual(texts, [])
        self.parser.logger.error.assert_called_with(f"Error extracting text from XPath {xpath}: XPath error")

    def test_get_element_attribute_success(self):
        """Test get_element_attribute method with a valid XPath and attribute."""
        root = ET.fromstring("<root><element attribute='value'>text</element></root>")
        xpath = "element"
        attribute = "attribute"
        value = self.parser.get_element_attribute(root, xpath, attribute)
        self.assertEqual(value, "value")
        self.parser.logger.debug.assert_called_with(f"Extracted attribute {attribute} from {xpath}: value")

    def test_get_element_attribute_element_not_found(self):
        """Test get_element_attribute method when the element is not found."""
        root = ET.fromstring("<root><element attribute='value'>text</element></root>")
        xpath = "nonexistent"
        attribute = "attribute"
        value = self.parser.get_element_attribute(root, xpath, attribute)
        self.assertIsNone(value)
        self.parser.logger.warning.assert_called_with(f"Element not found for XPath: {xpath}")

    def test_get_element_attribute_attribute_not_found(self):
        """Test get_element_attribute method when the attribute is not found."""
        root = ET.fromstring("<root><element>text</element></root>")
        xpath = "element"
        attribute = "nonexistent"
        value = self.parser.get_element_attribute(root, xpath, attribute)
        self.assertIsNone(value)
        self.parser.logger.debug.assert_called_with(f"Extracted attribute {attribute} from {xpath}: None")

    def test_get_element_attribute_exception(self):
        """Test get_element_attribute method when an exception occurs."""
        root = unittest.mock.MagicMock()
        root.find.side_effect = Exception("XPath error")
        xpath = "element"
        attribute = "attribute"
        value = self.parser.get_element_attribute(root, xpath, attribute)
        self.assertIsNone(value)
        self.parser.logger.error.assert_called_with(f"Error extracting attribute {attribute} from XPath {xpath}: XPath error")

    @patch("dewey.core.research.utils.sts_xml_parser.STSXmlParser.parse_args")
    @patch("dewey.core.research.utils.sts_xml_parser.STSXmlParser.run")
    def test_execute_success(self, mock_run, mock_parse_args):
        """Test the execute method with successful execution."""
        mock_args = unittest.mock.MagicMock()
        mock_parse_args.return_value = mock_args

        self.parser.execute()

        mock_parse_args.assert_called_once()
        mock_run.assert_called_once()
        self.parser.logger.info.assert_any_call(f"Starting execution of {self.parser.name}")
        self.parser.logger.info.assert_any_call(f"Completed execution of {self.parser.name}")

    @patch("dewey.core.research.utils.sts_xml_parser.STSXmlParser.parse_args")
    @patch("dewey.core.research.utils.sts_xml_parser.STSXmlParser.run", side_effect=KeyboardInterrupt)
    def test_execute_keyboard_interrupt(self, mock_run, mock_parse_args):
        """Test the execute method when a KeyboardInterrupt occurs."""
        mock_args = unittest.mock.MagicMock()
        mock_parse_args.return_value = mock_args

        with self.assertRaises(SystemExit) as cm:
            self.parser.execute()

        self.assertEqual(cm.exception.code, 1)
        self.parser.logger.warning.assert_called_with("Script interrupted by user")

    @patch("dewey.core.research.utils.sts_xml_parser.STSXmlParser.parse_args")
    @patch("dewey.core.research.utils.sts_xml_parser.STSXmlParser.run", side_effect=Exception("Some error"))
    def test_execute_exception(self, mock_run, mock_parse_args):
        """Test the execute method when an exception occurs."""
        mock_args = unittest.mock.MagicMock()
        mock_parse_args.return_value = mock_args

        with self.assertRaises(SystemExit) as cm:
            self.parser.execute()

        self.assertEqual(cm.exception.code, 1)
        self.parser.logger.error.assert_called_with("Error executing script: Some error", exc_info=True)

    def test_cleanup(self):
        """Test the _cleanup method."""
        self.parser.db_conn = unittest.mock.MagicMock()
        self.parser._cleanup()
        self.parser.db_conn.close.assert_called_once()
        self.parser.logger.debug.assert_called_with("Closing database connection")

    def test_cleanup_no_db_conn(self):
        """Test the _cleanup method when db_conn is None."""
        self.parser.db_conn = None
        self.parser._cleanup()
        # Assert that no methods were called on db_conn
        self.assertFalse(hasattr(self.parser, 'db_conn'))

    def test_cleanup_db_conn_exception(self):
        """Test the _cleanup method when closing the database connection raises an exception."""
        self.parser.db_conn = unittest.mock.MagicMock()
        self.parser.db_conn.close.side_effect = Exception("Close error")
        self.parser._cleanup()
        self.parser.logger.warning.assert_called_with("Error closing database connection: Close error")

    def test_get_path_absolute(self):
        """Test get_path method with an absolute path."""
        absolute_path = "/absolute/path"
        result = self.parser.get_path(absolute_path)
        self.assertEqual(result, Path(absolute_path))

    def test_get_path_relative(self):
        """Test get_path method with a relative path."""
        relative_path = "relative/path"
        expected_path = self.parser.PROJECT_ROOT / relative_path
        result = self.parser.get_path(relative_path)
        self.assertEqual(result, expected_path)

    def test_get_config_value_success(self):
        """Test get_config_value method with a valid key."""
        self.parser.config = {"section": {"key": "value"}}
        value = self.parser.get_config_value("section.key")
        self.assertEqual(value, "value")

    def test_get_config_value_default(self):
        """Test get_config_value method with a key that doesn't exist and a default value."""
        self.parser.config = {"section": {"key": "value"}}
        value = self.parser.get_config_value("section.nonexistent", "default")
        self.assertEqual(value, "default")

    def test_get_config_value_nested_missing(self):
        """Test get_config_value method with a nested key where an intermediate level is missing."""
        self.parser.config = {"section": {"key": "value"}}
        value = self.parser.get_config_value("nonexistent.key", "default")
        self.assertEqual(value, "default")

    def test_get_config_value_no_default(self):
        """Test get_config_value method with a key that doesn't exist and no default value."""
        self.parser.config = {"section": {"key": "value"}}
        value = self.parser.get_config_value("section.nonexistent")
        self.assertIsNone(value)

    @patch("dewey.core.research.utils.sts_xml_parser.logging")
    @patch("dewey.core.research.utils.sts_xml_parser.yaml")
    def test_setup_logging_from_config(self, mock_yaml, mock_logging):
        """Test _setup_logging method with configuration from dewey.yaml."""
        mock_yaml.safe_load.return_value = {
            'core': {
                'logging': {
                    'level': 'DEBUG',
                    'format': '%(levelname)s - %(message)s',
                    'date_format': '%Y-%m-%d',
                }
            }
        }
        mock_logging_config = unittest.mock.MagicMock()
        mock_logging.basicConfig = mock_logging_config
        mock_logger = unittest.mock.MagicMock()
        mock_logging.getLogger.return_value = mock_logger

        with patch("builtins.open", mock_open()):
            self.parser._setup_logging()

        mock_yaml.safe_load.assert_called_once()
        mock_logging.basicConfig.assert_called_once()
        mock_logging.getLogger.assert_called_once_with(self.parser.name)
        self.assertEqual(self.parser.logger, mock_logger)

    @patch("dewey.core.research.utils.sts_xml_parser.logging")
    @patch("dewey.core.research.utils.sts_xml_parser.yaml")
    def test_setup_logging_default_config(self, mock_yaml, mock_logging):
        """Test _setup_logging method with default logging configuration."""
        mock_yaml.safe_load.side_effect = FileNotFoundError
        mock_logging_config = unittest.mock.MagicMock()
        mock_logging.basicConfig = mock_logging_config
        mock_logger = unittest.mock.MagicMock()
        mock_logging.getLogger.return_value = mock_logger

        with patch("builtins.open", mock_open()):
            self.parser._setup_logging()

        mock_yaml.safe_load.assert_called_once()
        mock_logging.basicConfig.assert_called_once()
        mock_logging.getLogger.assert_called_once_with(self.parser.name)
        self.assertEqual(self.parser.logger, mock_logger)

    @patch("dewey.core.research.utils.sts_xml_parser.yaml")
    def test_load_config_success(self, mock_yaml):
        """Test _load_config method with a valid configuration file."""
        mock_yaml.safe_load.return_value = {"key": "value"}

        with patch("builtins.open", mock_open()):
            config = self.parser._load_config()

        self.assertEqual(config, {"key": "value"})
        self.parser.logger.debug.assert_called_with(f"Loading configuration from {self.parser.CONFIG_PATH}")

    @patch("dewey.core.research.utils.sts_xml_parser.yaml")
    def test_load_config_section_success(self, mock_yaml):
        """Test _load_config method with a valid configuration section."""
        self.parser.config_section = "section"
        mock_yaml.safe_load.return_value = {"section": {"key": "value"}}

        with patch("builtins.open", mock_open()):
            config = self.parser._load_config()

        self.assertEqual(config, {"key": "value"})
        self.parser.logger.debug.assert_called_with(f"Loading configuration from {self.parser.CONFIG_PATH}")

    @patch("dewey.core.research.utils.sts_xml_parser.yaml")
    def test_load_config_section_not_found(self, mock_yaml):
        """Test _load_config method when the configuration section is not found."""
        self.parser.config_section = "nonexistent"
        mock_yaml.safe_load.return_value = {"section": {"key": "value"}}

        with patch("builtins.open", mock_open()):
            config = self.parser._load_config()

        self.assertEqual(config, {"section": {"key": "value"}})
        self.parser.logger.warning.assert_called_with(
            "Config section 'nonexistent' not found in dewey.yaml. Using full config."
        )
        self.parser.logger.debug.assert_called_with(f"Loading configuration from {self.parser.CONFIG_PATH}")

    @patch("dewey.core.research.utils.sts_xml_parser.yaml")
    def test_load_config_file_not_found(self, mock_yaml):
        """Test _load_config method when the configuration file is not found."""
        mock_yaml.safe_load.side_effect = FileNotFoundError

        with patch("builtins.open", mock_open()):
            with self.assertRaises(FileNotFoundError):
                self.parser._load_config()

        self.parser.logger.error.assert_called_with(f"Configuration file not found: {self.parser.CONFIG_PATH}")

    @patch("dewey.core.research.utils.sts_xml_parser.yaml")
    def test_load_config_yaml_error(self, mock_yaml):
        """Test _load_config method when the configuration file has a YAML error."""
        mock_yaml.safe_load.side_effect = yaml.YAMLError("YAML error")

        with patch("builtins.open", mock_open()):
            with self.assertRaises(yaml.YAMLError):
                self.parser._load_config()

        self.parser.logger.error.assert_called_with(f"Error parsing YAML configuration: YAML error")

    @patch("dewey.core.research.utils.sts_xml_parser.get_connection")
    def test_initialize_db_connection_success(self, mock_get_connection):
        """Test _initialize_db_connection method with a successful database connection."""
        self.parser.config = {'core': {'database': {'db_url': 'test_url'}}}
        mock_conn = unittest.mock.MagicMock()
        mock_get_connection.return_value = mock_conn

        self.parser._initialize_db_connection()

        mock_get_connection.assert_called_with({'db_url': 'test_url'})
        self.assertEqual(self.parser.db_conn, mock_conn)
        self.parser.logger.debug.assert_called_with("Initializing database connection")
        self.parser.logger.debug.assert_called_with("Database connection established")

    @patch("dewey.core.research.utils.sts_xml_parser.get_connection", side_effect=ImportError)
    def test_initialize_db_connection_import_error(self, mock_get_connection):
        """Test _initialize_db_connection method when the database module cannot be imported."""
        with self.assertRaises(ImportError):
            self.parser._initialize_db_connection()

        self.parser.logger.error.assert_called_with("Could not import database module. Is it installed?")

    @patch("dewey.core.research.utils.sts_xml_parser.get_connection", side_effect=Exception("Connection error"))
    def test_initialize_db_connection_exception(self, mock_get_connection):
        """Test _initialize_db_connection method when an exception occurs during database connection."""
        self.parser.config = {'core': {'database': {'db_url': 'test_url'}}}
        with self.assertRaises(Exception) as context:
            self.parser._initialize_db_connection()

        self.assertEqual(str(context.exception), "Connection error")
        self.parser.logger.error.assert_called_with("Failed to initialize database connection: Connection error")

    @patch("dewey.core.research.utils.sts_xml_parser.get_llm_client")
    def test_initialize_llm_client_success(self, mock_get_llm_client):
        """Test _initialize_llm_client method with a successful LLM client initialization."""
        self.parser.config = {'llm': {'model': 'test_model'}}
        mock_llm_client = unittest.mock.MagicMock()
        mock_get_llm_client.return_value = mock_llm_client

        self.parser._initialize_llm_client()

        mock_get_llm_client.assert_called_with({'model': 'test_model'})
        self.assertEqual(self.parser.llm_client, mock_llm_client)
        self.parser.logger.debug.assert_called_with("Initializing LLM client")
        self.parser.logger.debug.assert_called_with("LLM client initialized")

    @patch("dewey.core.research.utils.sts_xml_parser.get_llm_client", side_effect=ImportError)
    def test_initialize_llm_client_import_error(self, mock_get_llm_client):
        """Test _initialize_llm_client method when the LLM module cannot be imported."""
        with self.assertRaises(ImportError):
            self.parser._initialize_llm_client()

        self.parser.logger.error.assert_called_with("Could not import LLM module. Is it installed?")

    @patch("dewey.core.research.utils.sts_xml_parser.get_llm_client", side_effect=Exception("LLM error"))
    def test_initialize_llm_client_exception(self, mock_get_llm_client):
        """Test _initialize_llm_client method when an exception occurs during LLM client initialization."""
        self.parser.config = {'llm': {'model': 'test_model'}}
        with self.assertRaises(Exception) as context:
            self.parser._initialize_llm_client()

        self.assertEqual(str(context.exception), "LLM error")
        self.parser.logger.error.assert_called_with("Failed to initialize LLM client: LLM error")

    def test_setup_argparse(self):
        """Test the setup_argparse method."""
        parser = self.parser.setup_argparse()
        self.assertIsInstance(parser, unittest.mock.ANY)  # Check if it's an instance of argparse.ArgumentParser
        self.assertTrue(parser.description == self.parser.description)

    def test_parse_args_log_level(self):
        """Test parse_args method with log level argument."""
        with patch("sys.argv", ["script.py", "--log-level", "DEBUG"]):
            args = self.parser.parse_args()
            self.assertEqual(self.parser.logger.level, logging.DEBUG)
            self.parser.logger.debug.assert_called_with("Log level set to DEBUG")

    @patch("dewey.core.research.utils.sts_xml_parser.yaml")
    def test_parse_args_config(self, mock_yaml):
        """Test parse_args method with config argument."""
        mock_yaml.safe_load.return_value = {"key": "value"}
        with patch("sys.argv", ["script.py", "--config", "config.yaml"]):
            with patch("builtins.open", mock_open()):
                args = self.parser.parse_args()
                self.assertEqual(self.parser.config, {"key": "value"})
                self.parser.logger.info.assert_called_with("Loaded configuration from config.yaml")

    @patch("dewey.core.research.utils.sts_xml_parser.yaml")
    def test_parse_args_config_not_found(self, mock_yaml):
        """Test parse_args method when the config file is not found."""
        with patch("sys.argv", ["script.py", "--config", "nonexistent.yaml"]):
            with patch("builtins.open", side_effect=FileNotFoundError):
                with self.assertRaises(SystemExit) as cm:
                    self.parser.parse_args()
                self.assertEqual(cm.exception.code, 1)
                self.assertTrue(self.parser.logger.error.called)

    @patch("dewey.core.research.utils.sts_xml_parser.get_connection")
    def test_parse_args_db_connection_string(self, mock_get_connection):
        """Test parse_args method with db_connection_string argument."""
        self.parser.requires_db = True
        mock_conn = unittest.mock.MagicMock()
        mock_get_connection.return_value = mock_conn
        with patch("sys.argv", ["script.py", "--db-connection-string", "test_connection_string"]):
            args = self.parser.parse_args()
            mock_get_connection.assert_called_with({"connection_string": "test_connection_string"})
            self.assertEqual(self.parser.db_conn, mock_conn)
            self.parser.logger.info.assert_called_with("Using custom database connection")

    @patch("dewey.core.research.utils.sts_xml_parser.get_llm_client")
    def test_parse_args_llm_model(self, mock_get_llm_client):
        """Test parse_args method with llm_model argument."""
        self.parser.enable_llm = True
        mock_llm_client = unittest.mock.MagicMock()
        mock_get_llm_client.return_value = mock_llm_client
        with patch("sys.argv", ["script.py", "--llm-model", "test_llm_model"]):
            args = self.parser.parse_args()
            mock_get_llm_client.assert_called_with({"model": "test_llm_model"})
            self.assertEqual(self.parser.llm_client, mock_llm_client)
            self.parser.logger.info.assert_called_with("Using custom LLM model: test_llm_model")

if __name__ == "__main__":
    unittest.main()
