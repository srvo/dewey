"""LLM agent for analyzing client communications from the database."""

from typing import Dict, List

from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from dewey.core.base_script import BaseScript
from dewey.core.db.connection import get_connection
from dewey.core.db.models import ClientCommunicationsIndex, ClientProfiles, Emails
from dewey.core.exceptions import DatabaseConnectionError, LLMError
from dewey.llm.litellm_client import LiteLLMClient, Message


class CommunicationAnalysis(BaseModel):
    """Structured output format for communication analysis."""

    summary: str
    key_topics: list[str]
    sentiment: str
    action_items: list[str]
    urgency: str
    client_concerns: list[str]
    communication_trends: list[str]


class CommunicationAnalyzerAgent(BaseScript):
    """LLM agent for analyzing client email communications."""

    def __init__(self):
        super().__init__(
            name="communication_analyzer",
            description="Analyzes client communications using LLMs",
            config_section="llm.agents.communication",
            enable_llm=True,
        )
        self.llm_client = LiteLLMClient()
        self.analysis_model = self.get_config_value("analysis_model", "gpt-4-turbo")

    def retrieve_communications(self, client_identifier: str) -> list[dict]:
        """Retrieve communications for a client.

        Args:
            client_identifier: Email address or client_profile_id

        Returns:
            List of communication dictionaries with subject, content, and dates

        """
        try:
            db_config = self.config.get("database", {})
            db_conn = get_connection(db_config)
            session = db_conn.get_session()
            try:
                # Try to find by email first
                query = (
                    session.query(ClientCommunicationsIndex)
                    .join(Emails)
                    .join(ClientProfiles)
                    .filter(
                        (ClientCommunicationsIndex.client_email == client_identifier)
                        | (ClientProfiles.id == client_identifier)
                    )
                    .options(joinedload(ClientCommunicationsIndex.email_analysis))
                )

                communications = query.limit(50).all()

                if not communications:
                    self.logger.warning(
                        f"No communications found for {client_identifier}"
                    )
                    return []

                return [
                    {
                        "subject": comm.Emails.subject,
                        "snippet": comm.Emails.snippet,
                        "sent_date": comm.Emails.analysis_date,
                        "direction": "inbound" if comm.client_email else "outbound",
                    }
                    for comm in communications
                ]

            except SQLAlchemyError as e:
                self.logger.error(f"Database error retrieving communications: {e}")
                raise DatabaseConnectionError("Failed to retrieve communications")
            finally:
                session.close()
                db_conn.close()

        except Exception as e:
            self.logger.error(f"Failed to initialize database connection: {e}")
            raise

    def format_communications_prompt(self, communications: list[dict]) -> list[Message]:
        """Format communications for LLM analysis."""
        system_prompt = """You are a financial communications analyst. Analyze client emails and:
1. Summarize key discussion points
2. Identify sentiment (positive, neutral, negative)
3. Extract action items
4. Assess urgency (low, medium, high)
5. Note client concerns
6. Identify communication trends

Return JSON format with: summary, key_topics, sentiment, action_items, urgency, client_concerns, communication_trends"""

        comms_text = "\n\n".join(
            f"Subject: {c['subject']}\n"
            f"Date: {c['sent_date']}\n"
            f"Direction: {c['direction']}\n"
            f"Content: {c['snippet']}\n"
            for c in communications
        )

        return [
            Message(role="system", content=system_prompt),
            Message(
                role="user", content=f"Analyze these communications:\n{comms_text}"
            ),
        ]

    def analyze_communications(self, client_identifier: str) -> CommunicationAnalysis:
        """Analyze client communications using LLM."""
        try:
            # Retrieve communications
            comms = self.retrieve_communications(client_identifier)
            if not comms:
                return CommunicationAnalysis(
                    summary="No communications found",
                    key_topics=[],
                    sentiment="neutral",
                    action_items=[],
                    urgency="low",
                    client_concerns=[],
                    communication_trends=[],
                )

            # Format and send to LLM
            messages = self.format_communications_prompt(comms)
            response = self.llm_client.generate_completion(
                messages=messages,
                model=self.analysis_model,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            # Parse and validate response
            return CommunicationAnalysis.parse_raw(response.choices[0].message.content)

        except LLMError as e:
            self.logger.error(f"LLM analysis failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            raise

    def execute(self) -> None:
        """BaseScript entry point for CLI usage."""
        parser = self.setup_argparse()
        parser.add_argument("client_identifier", help="Client email or ID")
        args = parser.parse_args()

        analysis = self.analyze_communications(args.client_identifier)
        self.logger.info(f"Analysis results:\n{analysis.json(indent=2)}")


if __name__ == "__main__":
    CommunicationAnalyzerAgent().run()
