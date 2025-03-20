import unittest
from unittest.mock import patch

from dewey.core.utils import MyUtils


class TestMyUtils(unittest.TestCase):
    @patch("dewey.core.utils.MyUtils.get_config_value")
    def test_example_utility_function(self, mock_get_config_value):
        mock_get_config_value.return_value = "test_value"
        utils = MyUtils()
        input_data = "test_input"
        result = utils.example_utility_function(input_data)
        self.assertEqual(result, f"Processed: {input_data}")

    def test_init(self):
        utils = MyUtils()
        self.assertIsInstance(utils, MyUtils)


if __name__ == "__main__":
    unittest.main()
