from dewey.core.base_script import BaseScript


class EmailProcessor(BaseScript):
    """A class for processing emails, adhering to Dewey project conventions."""

    def __init__(self):
        """Initializes the EmailProcessor with configurations."""
        super().__init__(
            config_section="crm.email", requires_db=True, enable_llm=True, name="EmailProcessor"
        )

    def execute(self) -> None:
        """Executes the core logic of the email processor.

        This method fetches emails, analyzes their content using LLM,
        and updates the database with the extracted information.
        """
        self.logger.info("Starting email processing...")

        # 1. Fetch emails
        max_emails = self.get_config_value("max_emails_per_run", 100)
        self.logger.debug(f"Maximum emails to process: {max_emails}")

        try:
            with self.db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT id, content FROM emails WHERE processed = FALSE LIMIT %s", (max_emails,))
                    emails = cursor.fetchall()
                    self.logger.info(f"Fetched {len(emails)} emails from the database.")

                    if not emails:
                        self.logger.info("No new emails to process.")
                        return

                    # 2. Analyze email content using LLM
                    for email_id, content in emails:
                        try:
                            prompt = f"Summarize the key points and action items from the following email: {content}"
                            if self.llm_client:
                                response = self.llm_client.generate_text(prompt)
                                summary = response.get("choices")[0].get("message").get("content") if response.get("choices") else "No summary available"
                                self.logger.info(f"LLM Summary for email {email_id}: {summary}")

                                # 3. Update database with analysis results
                                update_query = "UPDATE emails SET summary = %s, processed = TRUE WHERE id = %s"
                                cursor.execute(update_query, (summary, email_id))
                                conn.commit()
                                self.logger.info(f"Updated email {email_id} with summary.")
                            else:
                                self.logger.warning("LLM client not initialized. Skipping email summarization.")

                        except Exception as llm_err:
                            self.logger.error(f"LLM processing failed for email {email_id}: {llm_err}")

        except Exception as db_err:
            self.logger.error(f"Database operation failed: {db_err}")

        self.logger.info("Email processing completed.")


if __name__ == "__main__":
    processor = EmailProcessor()
    processor.execute()
