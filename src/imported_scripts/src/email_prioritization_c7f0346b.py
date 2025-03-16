"""Service for prioritizing emails based on user preferences and patterns."""

import json
import os
from pathlib import Path

import requests
import structlog
from database.models import Email, EventLog
from django.utils import timezone
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)


class PrioritySource:
    """Enum-like class for priority decision sources."""

    DEEP_INFRA = "deep_infra"
    DETERMINISTIC = "deterministic"
    MANUAL = "manual"


class EmailPrioritizer:
    """Service for scoring and prioritizing emails based on user preferences."""

    def __init__(self) -> None:
        """Initialize the prioritizer with configuration."""
        self.config_dir: Path = Path(__file__).parent / "config"
        self.preferences: dict = self._load_json("email_preferences.json")
        self.edge_cases: dict = self._load_json("edge_cases.json")
        self.logger = logger.bind(service="email_prioritizer")

    def _load_json(self, filename: str) -> dict:
        """Load a JSON configuration file.

        Args:
            filename: The name of the JSON file to load.

        Returns:
            A dictionary containing the JSON data. Returns an empty dictionary if loading fails.

        """
        try:
            with open(self.config_dir / filename) as f:
                return json.load(f)
        except Exception as e:
            self.logger.exception(
                "config_load_failed",
                filename=filename,
                error=str(e),
                error_type=type(e).__name__,
            )
            return {}

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(
            (requests.exceptions.RequestException, ValueError),
        ),
    )
    def _score_with_deepinfra(self, email: Email) -> tuple[int, float, str]:
        """Score email using DeepInfra API with retry logic.

        Args:
            email: The Email object to score.

        Returns:
            A tuple containing the priority, confidence, and reason for the score.

        Raises:
            ValueError: If DEEPINFRA_API_KEY is not set or if the API response is invalid.
            requests.exceptions.RequestException: If the API request fails.

        """
        api_key = os.getenv("DEEPINFRA_API_KEY")
        if not api_key:
            msg = "DEEPINFRA_API_KEY not set"
            raise ValueError(msg)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        content = f"Subject: {email.subject}\n\n{email.plain_body or ''}"

        try:
            response = requests.post(
                "https://api.deepinfra.com/v1/openai/chat/completions",
                headers=headers,
                json={
                    "model": "openchat/openchat_3.5",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert at analyzing email importance.",
                        },
                        {"role": "user", "content": f"Analyze this email:\n{content}"},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 100,
                },
                timeout=10,
            )

            response.raise_for_status()
            result = response.json()

            if not result.get("choices"):
                msg = "No choices in API response"
                raise ValueError(msg)

            content = result["choices"][0]["message"]["content"]
            result_json = json.loads(content)

            return (
                result_json["priority"],
                result_json["confidence"],
                result_json.get("reason", "AI analysis"),
            )

        except Exception as e:
            self.logger.exception(
                "deepinfra_scoring_failed",
                email_id=email.id,
                error=str(e),
            )
            raise

    def _deterministic_score(self, email: Email) -> tuple[int, float, str]:
        """Score an email based on predefined rules.

        Args:
            email: The Email object to score.

        Returns:
            A tuple containing the priority, confidence, and reason for the score.

        """
        priority = 1
        confidence = 0.8
        reasons: list[str] = []

        for source in self.preferences.get("high_priority_sources", []):
            if any(kw.lower() in email.subject.lower() for kw in source["keywords"]):
                priority = max(priority, source["min_priority"])
                reasons.append(source["reason"])
                confidence = 0.9

        for source in self.preferences.get("low_priority_sources", []):
            if any(kw.lower() in email.subject.lower() for kw in source["keywords"]):
                priority = min(priority, source.get("max_priority", 1))
                reasons.append(source["reason"])
                confidence = 0.9

        for config in self.preferences.get(
            "newsletter_defaults",
            {},
        ).values():
            if any(kw.lower() in email.subject.lower() for kw in config["keywords"]):
                priority = config["default_priority"]
                reasons.append(config["reason"])
                confidence = 0.95

        for rule in self.preferences.get("override_rules", []):
            if any(kw.lower() in email.subject.lower() for kw in rule["keywords"]):
                priority = max(priority, rule["min_priority"])
                reasons.append(rule["reason"])
                confidence = 0.95

        reason = " | ".join(reasons) if reasons else "Default priority"
        return priority, confidence, reason

    def score_email(self, email: Email) -> tuple[int, float, str]:
        """Score an email using multiple methods and return the best result.

        Args:
            email: The Email object to score.

        Returns:
            A tuple containing the priority, confidence, and reason for the score.

        """
        scores: list[tuple[int, float, str, str]] = []

        try:
            priority, confidence, reason = self._score_with_deepinfra(email)
            scores.append((priority, confidence, reason, PrioritySource.DEEP_INFRA))
        except Exception as e:
            self.logger.warning("ai_scoring_failed", email_id=email.id, error=str(e))

        try:
            priority, confidence, reason = self._deterministic_score(email)
            scores.append((priority, confidence, reason, PrioritySource.DETERMINISTIC))
        except Exception as e:
            self.logger.exception(
                "deterministic_scoring_failed",
                email_id=email.id,
                error=str(e),
            )

        if not scores:
            return 1, 0.5, "Scoring failed"

        priority, confidence, reason, source = max(scores, key=lambda x: x[1])

        if confidence < 0.7:
            self._log_edge_case(
                email,
                priority,
                confidence,
                f"Low confidence ({source})",
            )
        elif len(scores) > 1:
            priorities = [s[0] for s in scores]
            if max(priorities) - min(priorities) > 1:
                self._log_edge_case(
                    email,
                    priority,
                    confidence,
                    "Priority disagreement between methods",
                )

        return priority, confidence, reason

    def _log_edge_case(
        self,
        email: Email,
        priority: int,
        confidence: float,
        reason: str,
    ) -> None:
        """Log an edge case for analysis.

        Args:
            email: The Email object associated with the edge case.
            priority: The assigned priority.
            confidence: The confidence level of the priority assignment.
            reason: The reason for considering this an edge case.

        """
        edge_case = {
            "timestamp": timezone.now().isoformat(),
            "type": "potential_misclassification",
            "subject": email.subject,
            "priority": priority,
            "confidence": confidence,
            "reason": reason,
        }

        try:
            edge_cases = self._load_json("edge_cases.json")
            edge_cases.append(edge_case)

            with open(self.config_dir / "edge_cases.json", "w") as f:
                json.dump(edge_cases, f, indent=2)

        except Exception as e:
            self.logger.exception(
                "edge_case_logging_failed",
                error=str(e),
                error_type=type(e).__name__,
            )

        EventLog.objects.create(
            event_type="PRIORITY_EDGE_CASE",
            email=email,
            details=edge_case,
            performed_by="email_prioritizer",
        )
