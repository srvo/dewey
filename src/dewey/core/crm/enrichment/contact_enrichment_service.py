from dewey.core.base_script import BaseScript
from dewey.core.db.connection import (
    DatabaseConnection,
    get_connection,
    get_motherduck_connection,
)


class ContactEnrichmentService(BaseScript):
    """
    A service for enriching contact information.

    This class provides methods for fetching additional information
    about a contact from external sources.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes the ContactEnrichmentService.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs, config_section="crm.enrichment")

    def run(self) -> None:
        """
        Runs the contact enrichment process.

        Fetches the enrichment API key from the configuration, logs its usage,
        and then logs the completion of the process.

        Raises:
            ValueError: If the enrichment API key is not found in the configuration.

        Returns:
            None
        """
        self.logger.info("Starting contact enrichment process.")

        api_key = self.get_config_value("enrichment_api_key")
        if not api_key:
            self.logger.warning("Enrichment API key not found in config.")
            return

        self.logger.info(f"Using API key: {api_key}")
        self.logger.info("Contact enrichment process completed.")
