import unittest
from unittest.mock import patch

from dewey.core.utils import MyUtils


class TestMyUtils(unittest.TestCase):
    @patch("dewey.core.utils.MyUtils.get_config_value")
    @patch("dewey.core.utils.MyUtils.db_conn")
    @patch("dewey.core.utils.MyUtils.llm_client")
    def test_my_utils_initialization(self, mock_llm_client, mock_db_conn, mock_get_config_value):
        mock_get_config_value.return_value = "test_value"
        mock_db_conn.return_value = True
        mock_llm_client.return_value = True

        utils = MyUtils()
        self.assertIsInstance(utils, MyUtils)

    def test_example_utility_function(self):
        utils = MyUtils()
        input_data = "test_input"
        expected_output = "Processed: test_input"
        actual_output = utils.example_utility_function(input_data)
        self.assertEqual(actual_output, expected_output)


if __name__ == "__main__":
    unittest.main()
