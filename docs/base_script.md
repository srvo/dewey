# BaseScript System

The BaseScript system is a standardized framework for all scripts in the Dewey project. It enforces project conventions and provides consistent functionality across all scripts.

## Purpose

The BaseScript system serves to:

1. **Standardize Script Implementation**: Ensure all scripts follow a consistent pattern
2. **Centralize Configuration**: All scripts use the same configuration source (dewey.yaml)
3. **Provide Built-in Functionality**: Common features like logging, database connections, and LLM access
4. **Enforce Error Handling**: Consistent error handling and resource cleanup
5. **Simplify Script Development**: Reduce boilerplate code

## Usage

### Basic Usage

All scripts in the Dewey project must inherit from BaseScript:

```python
from dewey.core.base_script import BaseScript

class MyScript(BaseScript):
    def __init__(self):
        super().__init__(
            name="my_script",
            description="My script does something useful"
        )
    
    def run(self):
        # Your script implementation goes here
        self.logger.info("Running my script")
        result = self.process_data()
        self.logger.info(f"Processed {len(result)} items")
```

### Using Configuration

BaseScript automatically loads configuration from `config/dewey.yaml`. You can access it via `self.config`:

```python
def run(self):
    api_key = self.config.get('core', {}).get('api_keys', {}).get('my_service')
    self.logger.info(f"Using API key: {api_key}")
```

For scripts that need a specific config section, use the `config_section` parameter:

```python
def __init__(self):
    super().__init__(
        name="my_script",
        description="My script does something useful",
        config_section="my_module"  # Only load the 'my_module' section from dewey.yaml
    )
```

You can also use the `get_config_value` helper method with dot notation:

```python
api_key = self.get_config_value('core.api_keys.my_service', default='fallback_key')
```

### Database Access

For scripts requiring database access:

```python
def __init__(self):
    super().__init__(
        name="my_script",
        description="My script does something useful",
        requires_db=True  # Automatically set up database connection
    )

def run(self):
    # Use self.db_conn to access the database
    result = self.db_conn.execute("SELECT * FROM my_table")
```

### LLM Integration

For scripts that use LLM functionality:

```python
def __init__(self):
    super().__init__(
        name="my_script",
        description="My script does something useful",
        enable_llm=True  # Automatically set up LLM client
    )

def run(self):
    # Use self.llm_client to access LLM functionality
    response = self.llm_client.generate("Tell me about the weather")
```

### Path Handling

BaseScript provides a helper method to handle paths consistently:

```python
def run(self):
    # Get a path relative to project root
    data_path = self.get_path("data/my_dataset.csv")
    
    # Works with absolute paths too
    config_path = self.get_path("/etc/my_config.yaml")
```

### Command Line Arguments

BaseScript provides built-in argument parsing:

```python
def setup_argparse(self):
    parser = super().setup_argparse()
    parser.add_argument("--input", help="Input file path")
    parser.add_argument("--output", help="Output file path")
    return parser

def run(self):
    args = self.parse_args()
    input_path = args.input
    output_path = args.output
```

Common arguments like `--config` and `--log-level` are automatically added.

### Script Execution

BaseScript provides an `execute` method that handles the complete script lifecycle:

```python
if __name__ == "__main__":
    script = MyScript()
    script.execute()
```

This method:
1. Parses command line arguments
2. Sets up logging and configuration
3. Calls your `run()` method
4. Handles exceptions gracefully
5. Cleans up resources (e.g., database connections)

## Migration

If you have existing scripts that use an older pattern, use the migration script:

```bash
python scripts/migrate_script_init.py
```

This will update scripts to use the new BaseScript initialization pattern with proper parameters.

## Testing

Testing scripts that inherit from BaseScript is straightforward using the provided test helpers:

```python
from unittest.mock import patch, MagicMock
import unittest

class TestMyScript(unittest.TestCase):
    @patch('dewey.core.base_script.CONFIG_PATH')
    def test_my_script(self, mock_config_path):
        # Set up a test config
        mock_config_path.return_value = "path/to/test_config.yaml"
        
        # If your script uses the database
        with patch('dewey.core.db.connection.get_connection') as mock_get_connection:
            mock_db = MagicMock()
            mock_get_connection.return_value = mock_db
            
            # If your script uses LLM
            with patch('dewey.llm.llm_utils.get_llm_client') as mock_get_llm:
                mock_llm = MagicMock()
                mock_get_llm.return_value = mock_llm
                
                # Create your script instance
                script = MyScript()
                
                # Test its functionality
                script.run()
                
                # Verify expected behavior
                mock_db.execute.assert_called_with("SELECT * FROM my_table")
                mock_llm.generate.assert_called_with("Tell me about the weather")
```

## Best Practices

1. **Always inherit from BaseScript** for all non-test scripts
2. **Implement the `run()` method** - this is required
3. **Use the built-in logger** (`self.logger`) instead of creating your own
4. **Handle errors properly** within your `run()` method
5. **Clean up resources** in a `finally` block or let BaseScript handle it
6. **Use the right initialization parameters**:
   - `name`: A short, descriptive name for logging
   - `description`: A longer description for help text
   - `config_section`: The section in dewey.yaml to load
   - `requires_db`: Set to `True` if you need database access
   - `enable_llm`: Set to `True` if you need LLM functionality

## Troubleshooting

### Common Issues

1. **FileNotFoundError: dewey.yaml not found**
   - Make sure you're running the script from the project root
   - Check that config/dewey.yaml exists

2. **ImportError: No module named 'dewey.core.db.connection'**
   - If you use `requires_db=True`, make sure the database module is available

3. **ImportError: No module named 'dewey.llm.llm_utils'**
   - If you use `enable_llm=True`, make sure the LLM module is available

4. **Configuration section not found**
   - If you specify a `config_section` that doesn't exist, a warning is logged and the full config is used

### Debug Tips

1. Use `--log-level=DEBUG` when running your script for more detailed logs
2. Check the script initialization parameters to ensure they match your needs
3. Use proper exception handling in your `run()` method
4. Verify that required dependencies are installed 