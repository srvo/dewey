from typing import Any, Dict

from dewey.core.base_script import BaseScript


class EventCallback(BaseScript):
    """A class for handling event callbacks within the Dewey framework.

    This class inherits from BaseScript and provides a structured way to
    manage event-driven logic, utilizing Dewey's configuration and logging
    capabilities.
    """

    def __init__(self, config_section: str, event_data: dict[str, Any]) -> None:
        """Initializes the EventCallback with configuration and event data.

        Args:
            config_section (str): The configuration section for the script.
            event_data (Dict[str, Any]): A dictionary containing data
                associated with the event.

        """
        super().__init__(config_section=config_section)
        self.event_data = event_data

    def run(self) -> None:
        """Executes the core logic of the event callback.

        This method retrieves configuration values, processes event data,
        and logs relevant information using the Dewey logging system.

        Raises:
            ValueError: If a required configuration value is missing.

        """
        try:
            callback_url = self.get_config_value("callback_url")
            event_type = self.event_data.get("event_type", "unknown")

            self.logger.info(f"Received event of type: {event_type}")
            self.logger.info(f"Callback URL: {callback_url}")

            # Add your event processing logic here
            # Example:
            # response = requests.post(callback_url, json=self.event_data)
            # self.logger.info(f"Callback response: {response.status_code}")

        except KeyError as e:
            self.logger.error(f"Missing configuration value: {e}")
            raise ValueError(f"Required configuration missing: {e}")
        except Exception as e:
            self.logger.exception(f"Error processing event: {e}")
            raise

    def execute(self) -> None:
        """Executes the event callback logic.

        This method retrieves the callback URL from the configuration,
        logs the event type, and then attempts to post the event data
        to the callback URL.  Any exceptions during the process are
        logged and re-raised.
        """
        try:
            callback_url = self.get_config_value("callback_url")
            event_type = self.event_data.get("event_type", "unknown")

            self.logger.info(f"Executing event callback for event type: {event_type}")
            self.logger.debug(f"Callback URL: {callback_url}")
            self.logger.debug(f"Event Data: {self.event_data}")

            # TODO: Implement the actual HTTP POST request here.
            # Example using the 'requests' library:
            # import requests
            # response = requests.post(callback_url, json=self.event_data)
            # response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            # self.logger.info(f"Callback response status code: {response.status_code}")

            self.logger.info(f"Successfully executed event callback for event type: {event_type}")

        except KeyError as e:
            self.logger.error(f"Missing configuration value: {e}")
            raise ValueError(f"Required configuration missing: {e}")
        except Exception as e:
            self.logger.exception(f"Error during event callback execution: {e}")
            raise
