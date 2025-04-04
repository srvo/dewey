from dewey.core.base_script import BaseScript


class ScreenManager(BaseScript):
    """
    Manages the display and navigation of screens in the TUI.

    This class inherits from BaseScript and provides methods for
    initializing, displaying, and switching between different screens
    in the text-based user interface.
    """

    def __init__(self) -> None:
        """Initializes the ScreenManager."""
        super().__init__(config_section="screen_manager")
        self.logger.debug("ScreenManager initialized.")

    def run(self) -> None:
        """Runs the main loop of the screen manager."""
        self.logger.info("Starting screen manager...")
        # Example of accessing a configuration value
        default_screen = self.get_config_value("default_screen", "MainScreen")
        self.logger.debug(f"Default screen: {default_screen}")
        # Add screen initialization and display logic here
        print("Placeholder for screen display logic.")

    def display_screen(self, screen_name: str) -> None:
        """
        Displays the specified screen.

        Args:
        ----
            screen_name: The name of the screen to display.

        """
        self.logger.info(f"Displaying screen: {screen_name}")
        # Add logic to display the screen here
        print(f"Displaying screen: {screen_name}")

    def execute(self) -> None:
        """
        Executes the screen management logic.

        This method initializes and manages the display of screens
        within the text-based user interface. It retrieves the default
        screen from the configuration and displays it.
        """
        self.logger.info("Executing screen manager...")
        default_screen = self.get_config_value("default_screen", "MainScreen")
        self.logger.debug(f"Default screen: {default_screen}")
        self.display_screen(default_screen)
        self.logger.info("Screen manager execution completed.")


if __name__ == "__main__":
    screen_manager = ScreenManager()
    screen_manager.run()
