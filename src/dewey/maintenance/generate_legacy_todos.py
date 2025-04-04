from typing import Any

from dewey.core.base_script import BaseScript


class GenerateLegacyTodos(BaseScript):
    """A script to generate legacy todos."""

    def __init__(self) -> None:
        """Initializes the GenerateLegacyTodos script."""
        super().__init__(config_section="generate_legacy_todos")

    def execute(self) -> None:
        """
        Executes the legacy todo generation process.

        This method retrieves configuration values, iterates through data,
        and generates todos based on certain conditions.

        Raises
        ------
            Exception: If there is an error during the todo generation process.

        Returns
        -------
            None

        """
        try:
            example_config_value = self.get_config_value("example_config_key")
            self.logger.info(f"Using example config value: {example_config_value}")

            # Example data (replace with actual data source)
            data: list[dict[str, Any]] = [
                {"id": 1, "name": "Item A", "status": "pending"},
                {"id": 2, "name": "Item B", "status": "completed"},
                {"id": 3, "name": "Item C", "status": "pending"},
            ]

            for item in data:
                if item["status"] == "pending":
                    todo_message = (
                        f"Legacy TODO: Process item {item['name']} (ID: {item['id']})"
                    )
                    self.logger.warning(todo_message)  # Log as warning for visibility

                    if not self.dry_run:
                        # Simulate database/LLM interaction (replace with actual logic)
                        self.logger.info(f"Creating TODO for item {item['id']}...")
                        # database.create_todo(item["id"], todo_message)
                        # llm.analyze_and_assign(todo_message)
                    else:
                        self.logger.info(
                            f"[Dry Run] Would create TODO for item {item['id']}",
                        )

            self.logger.info("Legacy todo generation process completed.")

        except Exception as e:
            self.logger.exception(
                f"An error occurred during legacy todo generation: {e}",
            )
            raise

    def run(self) -> None:
        """
        Legacy method for backward compatibility.

        New scripts should implement execute() instead of run().
        This method will be deprecated in a future version.
        """
        self.logger.warning(
            "Using deprecated run() method. Update to use execute() instead.",
        )
        try:
            self.logger.info(f"Starting execution of {self.name}")

            # Call execute method
            self.execute()

            self.logger.info(f"Successfully completed {self.name}")
        except Exception as e:
            self.logger.error(f"Error executing {self.name}: {e}", exc_info=True)
            raise
        finally:
            self._cleanup()


# Example usage (for demonstration purposes)
if __name__ == "__main__":
    # Initialize and run the script
    script = GenerateLegacyTodos()
    script.run()
