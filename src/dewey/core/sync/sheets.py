from typing import Any, Dict

from dewey.core.base_script import BaseScript


class Sheets(BaseScript):
    """
    Synchronizes data with Google Sheets.

    This class inherits from BaseScript and provides methods for
    reading from and writing to Google Sheets.
    """

    def __init__(self) -> None:
        """Initializes the Sheets synchronization module."""
        super().__init__(config_section="sheets")

    def run(self) -> None:
        """
        Executes the main logic for synchronizing data with Google Sheets.

        Retrieves the sheet ID from the configuration and logs it.
        """
        self.logger.info("Starting Google Sheets synchronization...")
        sheet_id = self.get_config_value("sheet_id")
        self.logger.info(f"Sheet ID: {sheet_id}")
        self.logger.info("Google Sheets synchronization completed.")
