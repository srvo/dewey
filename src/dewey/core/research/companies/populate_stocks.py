from dewey.core.base_script import BaseScript
from typing import Optional


class PopulateStocks(BaseScript):
    """
    Populates stock data.

    This class inherits from BaseScript and provides methods for
    fetching and storing stock information.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        config_section: Optional[str] = None,
        requires_db: bool = True,
        enable_llm: bool = False,
    ) -> None:
        """
        Initializes the PopulateStocks module.

        Args:
            name (Optional[str]): Name of the script (used for logging). Defaults to None.
            description (Optional[str]): Description of the script. Defaults to None.
            config_section (Optional[str]): Section in dewey.yaml to load for this script. Defaults to None.
            requires_db (bool): Whether this script requires database access. Defaults to True.
            enable_llm (bool): Whether this script requires LLM access. Defaults to False.
        """
        super().__init__(
            name=name,
            description=description,
            config_section=config_section,
            requires_db=requires_db,
            enable_llm=enable_llm,
        )

    def run(self) -> None:
        """
        Executes the stock population process.

        This method fetches the API key from the configuration, logs its usage,
        and then simulates fetching and storing stock data.  It uses the
        logger for all output.
        """
        api_key = self.get_config_value("api_key")
        self.logger.info(f"Using API key: {api_key}")
        # Implement your logic here to fetch and store stock data
        self.logger.info("Stock population process completed.")
