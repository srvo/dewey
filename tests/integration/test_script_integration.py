"""Integration tests for scripts using BaseScript."""

import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

# Add project root to path to make imports work
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dewey.core.base_script import BaseScript


class ScriptIntegrationTests(unittest.TestCase):
    """Test the integration of BaseScript with other scripts."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary config file
        self.test_config = {
            'core': {
                'logging': {'level': 'INFO'},
                'database': {'connection_string': 'mock://database'}
            },
            'llm': {'model': 'test-model'}
        }
        
        # Mock config path
        self.config_patcher = patch('dewey.core.base_script.CONFIG_PATH')
        self.mock_config_path = self.config_patcher.start()
        
        # Set up the mocked config file
        self.temp_config = Path(PROJECT_ROOT) / "tests" / "test_config.yaml"
        with open(self.temp_config, 'w') as f:
            yaml.dump(self.test_config, f)
        self.mock_config_path.return_value = self.temp_config
        
        # Mock DB connection and LLM client to avoid actual connections
        self.db_patcher = patch('dewey.core.db.connection.get_connection')
        self.mock_db = self.db_patcher.start()
        self.mock_db.return_value = MagicMock()
        
        self.llm_patcher = patch('dewey.llm.llm_utils.get_llm_client')
        self.mock_llm = self.llm_patcher.start()
        self.mock_llm.return_value = MagicMock()
        
        # Mock argparse to avoid command line args
        self.args_patcher = patch('argparse.ArgumentParser.parse_args')
        self.mock_args = self.args_patcher.start()
        self.mock_args.return_value = MagicMock(config=None, log_level=None)
        
        # Mock system exit
        self.exit_patcher = patch('sys.exit')
        self.mock_exit = self.exit_patcher.start()
        
    def tearDown(self):
        """Tear down test fixtures."""
        self.config_patcher.stop()
        self.db_patcher.stop()
        self.llm_patcher.stop()
        self.args_patcher.stop()
        self.exit_patcher.stop()
        
        # Remove temporary config file
        if self.temp_config.exists():
            self.temp_config.unlink()

    @patch('dewey.core.base_script.load_dotenv')
    def test_import_script_updater(self, _):
        """Test that the script_updater module can be imported and is compatible with BaseScript."""
from scripts.update_scripts import ScriptUpdater
        
        # Verify it inherits from BaseScript
        self.assertTrue(issubclass(ScriptUpdater, BaseScript))
        
        # Instantiate the class to test
        updater = ScriptUpdater(dry_run=True)
        
        # Check that it has the expected attributes
        self.assertEqual(updater.name, "script_updater")
        self.assertTrue(hasattr(updater, 'logger'))
        self.assertTrue(hasattr(updater, 'config'))
        self.assertTrue(hasattr(updater, 'run'))
        self.assertTrue(callable(updater.run))

    def _find_script_modules(self):
        """Find script modules in src/dewey that might use BaseScript."""
        script_modules = []
        
        # Check main script directories
        script_dirs = [
            Path(PROJECT_ROOT) / "src" / "dewey" / "core",
            Path(PROJECT_ROOT) / "src" / "dewey" / "maintenance",
            Path(PROJECT_ROOT) / "src" / "dewey" / "llm"
        ]
        
        for script_dir in script_dirs:
            if not script_dir.exists():
                continue
                
            for file in script_dir.glob("**/*.py"):
                # Skip __init__.py and special files
                if file.name.startswith("__") or file.name == "base_script.py":
                    continue
                    
                rel_path = file.relative_to(PROJECT_ROOT / "src")
                module_path = str(rel_path).replace("/", ".").replace(".py", "")
                script_modules.append(module_path)
                
        return script_modules

    @patch('dewey.core.base_script.load_dotenv')
    def test_random_script_sample(self, _):
        """Test a random sample of scripts to ensure they use BaseScript if needed."""
        scripts_tested = 0
        script_modules = self._find_script_modules()
        
        # Test up to 5 random scripts
import random
        random.shuffle(script_modules)
        
        for module_path in script_modules[:5]:
            try:
                module = importlib.import_module(module_path)
                
                # Find classes in the module
                for name in dir(module):
                    obj = getattr(module, name)
                    
                    # Skip if it's not a class or is BaseScript itself
                    if not isinstance(obj, type) or obj is BaseScript:
                        continue
                        
                    # Check if it's a script class (has a run method)
                    if hasattr(obj, 'run') and callable(getattr(obj, 'run')):
                        # Skip test classes
                        if 'Test' in name:
                            continue
                            
                        self.assertTrue(
                            issubclass(obj, BaseScript),
                            f"Class {name} in {module_path} should inherit from BaseScript"
                        )
                        scripts_tested += 1
                        
                        # Try to instantiate the class
                        try:
                            instance = obj()
                            self.assertTrue(hasattr(instance, 'logger'))
                            self.assertTrue(hasattr(instance, 'config'))
                        except Exception as e:
                            # Some classes might require specific init params, that's okay
                            pass
            except (ImportError, AttributeError) as e:
                # Skip modules that can't be imported or have circular dependencies
                continue
                
        self.assertGreaterEqual(scripts_tested, 1, "At least one script should have been tested")


if __name__ == '__main__':
    unittest.main() 