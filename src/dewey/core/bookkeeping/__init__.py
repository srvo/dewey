from dewey.core.base_script import BaseScript


class BookkeepingScript(BaseScript):
    """
    Base class for bookkeeping-related scripts.

    This class inherits from BaseScript and provides a common
    foundation for bookkeeping scripts, including configuration
    loading and database connection management.
    """

    def __init__(self, config_section: str = "bookkeeping") -> None:
        """
        Initializes the BookkeepingScript.

        Args:
            config_section (str, optional): The configuration section
                to use from the dewey.yaml file. Defaults to 'bookkeeping'.
        """
        super().__init__(
            name=self.__class__.__name__,
            description=self.__doc__,
            config_section=config_section,
            requires_db=True,
            enable_llm=False,
        )

    def run(self) -> None:
        """
        Abstract method to be implemented by subclasses.

        This method contains the core logic of the bookkeeping script.
        """
        raise NotImplementedError("Subclasses must implement the run method.")
