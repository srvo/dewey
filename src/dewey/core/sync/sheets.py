from dewey.core.base_script import BaseScript
import gspread


class Sheets(BaseScript):
    """Synchronizes data with Google Sheets.

    This class inherits from BaseScript and provides methods for
    reading from and writing to Google Sheets.
    """

    def __init__(self) -> None:
        """Initializes the Sheets synchronization module."""
        super().__init__(config_section="sheets")

    def run(self) -> None:
        """Executes the main logic for synchronizing data with Google Sheets.

        Retrieves the sheet ID from the configuration and logs it.
        """
        self.logger.info("Starting Google Sheets synchronization...")
        sheet_id = self.get_config_value("sheet_id")
        self.logger.info(f"Sheet ID: {sheet_id}")
        self.logger.info("Google Sheets synchronization completed.")

    def execute(self) -> None:
        """Executes the data synchronization with Google Sheets.

        Reads data from the specified Google Sheet and logs the dimensions of the data.
        """
        self.logger.info("Executing Google Sheets data synchronization...")
        sheet_id = self.get_config_value("sheet_id")
        try:
            # Authenticate with Google Sheets API
            gc = gspread.service_account(
                filename=self.get_config_value("credentials_path")
            )
            # Open the Google Sheet
            sheet = gc.open_by_key(sheet_id).sheet1
            # Get all values from the sheet
            data = sheet.get_all_values()
            num_rows = len(data)
            num_cols = len(data[0]) if data else 0

            self.logger.info(f"Successfully read data from Google Sheet '{sheet_id}'.")
            self.logger.info(
                f"Number of rows: {num_rows}, Number of columns: {num_cols}"
            )

        except Exception as e:
            self.logger.error(
                f"Error during Google Sheets synchronization: {e}", exc_info=True
            )
            raise
        finally:
            self.logger.info("Google Sheets data synchronization completed.")
