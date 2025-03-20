from dewey.core.base_script import BaseScript


class ContactEnrichmentService(BaseScript):
    """
    A service for enriching contact information.

    This class provides methods for fetching additional information
    about a contact from external sources.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self) -> None:
        """Runs the contact enrichment process."""
        self.logger.info("Starting contact enrichment process.")
        # Implement enrichment logic here
        api_key = self.get_config_value("enrichment_api_key")
        if not api_key:
            self.logger.warning("Enrichment API key not found in config.")
            return

        self.logger.info(f"Using API key: {api_key}")
        self.logger.info("Contact enrichment process completed.")
