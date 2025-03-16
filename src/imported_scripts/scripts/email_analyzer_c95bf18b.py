"""Email analysis with sender history preference."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import requests
from dotenv import load_dotenv
from scripts.config import Config
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Enumeration of available AI models for email analysis.

    Attributes:
        PHI4: Microsoft's Phi-4 model - lightweight and efficient
        MISTRAL: Mistral 7B v0.3 model with function calling capabilities
        NEMO: 12B parameter model with enhanced reasoning capabilities

    """

    PHI4 = "microsoft/phi-4"
    MISTRAL = "mistralai/Mistral-7B-Instruct-v0.3"
    NEMO = "mistralai/Mistral-Nemo-Instruct-2407"


@dataclass
class ModelConfig:
    """Configuration parameters for model inference.

    Attributes:
        temperature (float): Controls randomness (0.0-1.0). Lower = more deterministic
        max_tokens (int): Maximum number of tokens to generate
        top_p (float): Nucleus sampling probability threshold
        presence_penalty (float): Penalizes new tokens based on presence in text
        frequency_penalty (float): Penalizes new tokens based on frequency in text
        response_format (Dict): Format of the response (defaults to JSON)

    """

    temperature: float = 0.1
    max_tokens: int = 1000
    top_p: float = 1.0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    response_format: dict = field(default_factory=lambda: {"type": "json"})


@dataclass
class EmailAnalysis:
    """Container for email analysis results with metadata.

    Attributes:
        email_id (str): Unique identifier for the email
        scores (Dict): Structured analysis scores including:
            - automation: Likelihood email is automated
            - content: Content quality score
            - human: Human interaction probability
            - time: Time sensitivity score
            - business: Business relevance score
        metadata (Dict): Additional metadata about the email including:
            - source: Email source classification
            - topic: Main topics detected
        sender_history (Dict): Historical interaction data with sender
        latency (float): Time taken for analysis in seconds
        model_used (ModelType): AI model used for analysis
        timestamp (datetime): When analysis was performed (defaults to now)

    """

    email_id: str
    scores: dict
    metadata: dict
    sender_history: dict
    latency: float
    model_used: ModelType
    timestamp: datetime = datetime.now()


class EmailAnalyzer:
    """Core class for analyzing emails with contextual awareness.

    Handles email analysis using AI models while incorporating sender history
    and interaction patterns to provide more accurate results.

    Attributes:
        config (Config): Application configuration
        prompt (str): System prompt for analysis
        api_key (str): DeepInfra API key
        default_model (ModelType): Default model for analysis
        known_senders (Set[str]): Set of email addresses we've previously interacted with

    """

    def __init__(self, default_model: ModelType = ModelType.NEMO) -> None:
        """Initialize the email analyzer.

        Args:
            default_model: Default model to use for analysis

        """
        self.config = Config()
        with open(self.config.SYSTEM_PROMPTS / "email_analysis.txt") as f:
            self.prompt = f.read()

        # Load API key from .env
        self.api_key = os.getenv("DEEPINFRA_API_KEY")
        if not self.api_key:
            msg = "DEEPINFRA_API_KEY not set in .env file"
            raise ValueError(msg)
        if len(self.api_key) < 32:
            msg = "DEEPINFRA_API_KEY appears invalid - check .env file"
            raise ValueError(msg)

        # Set default model
        self.default_model = default_model

        # Cache of known senders
        self.known_senders: set[str] = set()
        self._load_sender_history()

    def _load_sender_history(self) -> None:
        """Load historical sender data from database.

        Populates self.known_senders with email addresses we've previously
        replied to, based on the is_replied flag in the raw_emails table.
        """
        try:
            with sqlite3.connect(self.config.DB_PATH) as conn:
                cursor = conn.cursor()
                # Get unique senders we've replied to (using is_replied flag)
                cursor.execute(
                    """
                    SELECT DISTINCT from_email
                    FROM raw_emails
                    WHERE is_replied = 1
                """,
                )
                self.known_senders = {row[0] for row in cursor.fetchall()}
                logger.info(f"Loaded {len(self.known_senders)} known senders")
        except Exception as e:
            logger.exception(f"Error loading sender history: {e}")
            self.known_senders = set()

    def _get_sender_history(self, from_email: str) -> dict:
        """Retrieve interaction history for a specific sender.

        Args:
            from_email: Email address of the sender

        Returns:
            Contains interaction statistics including:
                - is_known_sender: Whether we've replied before
                - total_emails: Total emails received from this sender
                - total_replies: Number of times we've replied
                - first_contact: Date of first contact
                - last_contact: Date of last contact
                - response_rate: Ratio of replies to total emails

        """
        try:
            with sqlite3.connect(self.config.DB_PATH) as conn:
                cursor = conn.cursor()
                # Get basic stats about our interaction history
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total_emails,
                        SUM(CASE WHEN is_replied = 1 THEN 1 ELSE 0 END) as replies,
                        MIN(received_date) as first_contact,
                        MAX(received_date) as last_contact
                    FROM raw_emails
                    WHERE from_email = ?
                """,
                    (from_email,),
                )
                row = cursor.fetchone()

                if row:
                    return {
                        "is_known_sender": from_email in self.known_senders,
                        "total_emails": row[0],
                        "total_replies": row[1],
                        "first_contact": row[2],
                        "last_contact": row[3],
                        "response_rate": row[1] / row[0] if row[0] > 0 else 0,
                    }
        except Exception as e:
            logger.exception(f"Error getting sender history: {e}")

        return {
            "is_known_sender": False,
            "total_emails": 0,
            "total_replies": 0,
            "first_contact": None,
            "last_contact": None,
            "response_rate": 0,
        }

    def _get_model_config(self, model: ModelType) -> ModelConfig:
        """Get optimal configuration parameters for a specific model.

        Args:
            model: The model to get configuration for

        Returns:
            Configuration parameters optimized for the model

        """
        if model == ModelType.NEMO:
            return ModelConfig(
                temperature=0.35,  # Recommended temp for Nemo
                max_tokens=1000,
                top_p=0.9,
                presence_penalty=0.1,
                frequency_penalty=0.1,
            )
        if model == ModelType.MISTRAL:
            return ModelConfig(
                temperature=0.1,
                max_tokens=1000,
                top_p=0.9,
                presence_penalty=0.1,
                frequency_penalty=0.1,
            )
        return ModelConfig()  # Default config for other models

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(
            (requests.exceptions.RequestException, ValueError),
        ),
    )
    def analyze_email(
        self,
        email_id: str,
        email_content: str,
        from_email: str,
        model: ModelType | None = None,
        model_config: ModelConfig | None = None,
    ) -> EmailAnalysis:
        """Analyze an email using AI models with sender context.

        Performs comprehensive analysis of email content while incorporating
        historical interaction data with the sender. Uses retry logic for
        API calls and handles various error conditions.

        Args:
            email_id: Unique identifier for the email
            email_content: Full email content including headers and body
            from_email: Sender's email address
            model: Specific model to use (defaults to default_model)
            model_config: Custom model configuration

        Returns:
            Complete analysis results including scores, metadata,
            and historical context

        Raises:
            ValueError: If API key is invalid or response format is incorrect
            requests.exceptions.RequestException: For API communication errors

        """
        start_time = datetime.now()
        model = model or self.default_model
        config = model_config or self._get_model_config(model)

        sender_history = self._get_sender_history(from_email)
        context = self._build_context(from_email, sender_history)

        # Verify API key is set and valid format
        if not self.api_key or len(self.api_key) < 32:
            msg = "Invalid DEEPINFRA_API_KEY format"
            raise ValueError(msg)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = self._call_deepinfra_api(
                model,
                config,
                headers,
                email_content,
                context,
            )
            analysis = self._parse_response(response)

            # Adjust scores based on sender history
            analysis = self._adjust_scores(analysis, sender_history)

            return EmailAnalysis(
                email_id=email_id,
                scores=analysis["scores"],
                metadata=analysis["metadata"],
                sender_history=sender_history,
                latency=(datetime.now() - start_time).total_seconds(),
                model_used=model,
            )
        except requests.exceptions.RequestException as e:
            logger.exception(f"API request failed: {e}")
            if hasattr(e.response, "text"):
                logger.exception(f"API response: {e.response.text}")
            raise
        except (json.JSONDecodeError, KeyError) as e:
            logger.exception(f"Error parsing model response: {e}")
            msg = "Invalid response format"
            raise ValueError(msg)

    def _build_context(self, from_email: str, sender_history: dict) -> str:
        """Build the context string for the AI model.

        Args:
            from_email: Sender's email address
            sender_history: Historical interaction data with the sender

        Returns:
            Context string to be included in the prompt.

        """
        return (
            f"\nAdditional context:"
            f"\n- Sender ({from_email}) "
            f"{'is' if sender_history['is_known_sender'] else 'is not'} "
            f"someone we've replied to before"
            f"\n- We've received {sender_history['total_emails']} emails from this sender"
            f"\n- We've replied {sender_history['total_replies']} times"
        )

    def _call_deepinfra_api(
        self,
        model: ModelType,
        config: ModelConfig,
        headers: dict[str, str],
        email_content: str,
        context: str,
    ) -> requests.Response:
        """Call the DeepInfra API to analyze the email content.

        Args:
            model: The AI model to use for analysis.
            config: Model configuration parameters.
            headers: HTTP headers for the API request.
            email_content: The content of the email to analyze.
            context: Contextual information to include in the prompt.

        Returns:
            The API response.

        Raises:
            requests.exceptions.RequestException: If the API request fails.

        """
        try:
            response = requests.post(
                "https://api.deepinfra.com/v1/openai/chat/completions",
                headers=headers,
                json={
                    "model": model.value,
                    "messages": [
                        {"role": "system", "content": self.prompt},
                        {
                            "role": "user",
                            "content": f"Analyze this email with context:\n{context}\n\nEmail content:\n{email_content}",
                        },
                    ],
                    "temperature": config.temperature,
                    "max_tokens": config.max_tokens,
                    "top_p": config.top_p,
                    "presence_penalty": config.presence_penalty,
                    "frequency_penalty": config.frequency_penalty,
                    "response_format": config.response_format,
                },
                timeout=10,
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.exception(f"API request failed: {e}")
            if hasattr(e.response, "text"):
                logger.exception(f"API response: {e.response.text}")
            raise

    def _parse_response(self, response: requests.Response) -> dict:
        """Parse the API response and extract the analysis results.

        Args:
            response: The API response.

        Returns:
            The parsed analysis results.

        Raises:
            ValueError: If the API response is invalid or the analysis results
                cannot be extracted.

        """
        try:
            result = response.json()

            if not result.get("choices"):
                msg = "No choices in API response"
                raise ValueError(msg)

            content = result["choices"][0]["message"]["content"]
            return json.loads(content)
        except (json.JSONDecodeError, KeyError) as e:
            logger.exception(f"Error parsing model response: {e}")
            msg = "Invalid response format"
            raise ValueError(msg)

    def _adjust_scores(self, analysis: dict, sender_history: dict) -> dict:
        """Adjust the analysis scores based on sender history.

        Args:
            analysis: The analysis results.
            sender_history: Historical interaction data with the sender.

        Returns:
            The adjusted analysis results.

        """
        if sender_history["is_known_sender"]:
            # Boost human interaction score for known senders
            if "human_interaction" in analysis["scores"]:
                analysis["scores"]["human_interaction"]["score"] = min(
                    1.0,
                    analysis["scores"]["human_interaction"]["score"] * 1.2,
                )
            # Reduce automation score for known senders
            if "automation_score" in analysis["scores"]:
                analysis["scores"]["automation_score"]["score"] = max(
                    0.0,
                    analysis["scores"]["automation_score"]["score"] * 0.8,
                )
        return analysis
