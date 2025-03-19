"""Config class to provide access to centralized configuration."""
from dewey.core.base_script import BaseScript

class CustomScript(BaseScript):
    def __init__(self):
        super().__init__(config_section='custom')

    def run(self):
        # Implement script logic here
        self.logger.info("Custom script running")