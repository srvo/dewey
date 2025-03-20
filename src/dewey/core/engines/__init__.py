from abc import abstractmethod

from dewey.core.base_script import BaseScript


class EngineScript(BaseScript):
    """
    Base class for engine scripts in the Dewey project.

    This class extends BaseScript and provides a standardized way to
    create and manage engine-related scripts.

    Attributes:
        config_section (str): The section in the dewey.yaml configuration file
            that contains the settings for this engine.
        requires_db (bool): Whether this script requires database access.
        enable_llm (bool): Whether this script requires LLM access.

    Args:
        config_section (str, optional): The section in dewey.yaml to load.
            Defaults to None.
        requires_db (bool, optional): Whether the script needs database access.
            Defaults to False.
        enable_llm (bool, optional): Whether the script needs LLM access.
            Defaults to False.
    """

    def __init__(
        self,
        config_section: str = None,
        requires_db: bool = False,
        enable_llm: bool = False,
    ) -> None:
        """
        Initialize the EngineScript.

        Args:
            config_section (str, optional): The section in dewey.yaml to load.
                Defaults to None.
            requires_db (bool, optional): Whether the script needs database access.
                Defaults to False.
            enable_llm (bool, optional): Whether the script needs LLM access.
                Defaults to False.
        """
        super().__init__(
            config_section=config_section,
            requires_db=requires_db,
            enable_llm=enable_llm,
        )

    @abstractmethod
    def run(self) -> None:
        """
        Abstract method to be implemented by subclasses.

        This method contains the core logic of the engine script.
        """
        pass
