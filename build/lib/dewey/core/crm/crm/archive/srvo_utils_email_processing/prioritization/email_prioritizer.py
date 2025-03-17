"""Service for prioritizing emails based on user preferences and patterns."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import structlog
from django.utils import timezone
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
import requests

from database.models import Email, EventLog

logger = structlog.get_logger(__name__)


class PrioritySource:
    """Enum-like class for priority decision sources."""

    DEEP_INFRA = "deep_infra"
    DETERMINISTIC = "deterministic"
    MANUAL = "manual"


class EmailPrioritizer:
    """Service for scoring and prioritizing emails based on user preferences."""

    def __init__(self):
        """Initialize the prioritizer with configuration."""
        self.config_dir = Path(__file__).parent / "config"
        self.preferences = self._load_json("email_preferences.json")
        self.edge_cases = self._load_json("edge_cases.json")
        self.logger = logger.bind(service="email_prioritizer")

    def _load_json(self, filename: str) -> Dict:
        """Load a JSON configuration file."""
        try:
            with open(self.config_dir / filename) as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(
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
            (requests.exceptions.RequestException, ValueError)
        ),
    )
    def _score_with_deepinfra(self, email: Email) -> Tuple[int, float, str]:
        """Score email using DeepInfra API with retry logic."""
        api_key = os.getenv("DEEPINFRA_API_KEY")
        if not api_key:
            raise ValueError("DEEPINFRA_API_KEY not set")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Prepare email content for analysis
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
                raise ValueError("No choices in API response")

            content = result["choices"][0]["message"]["content"]
            result_json = json.loads(content)

            return (
                result_json["priority"],
                result_json["confidence"],
                result_json.get("reason", "AI analysis"),
            )

        except Exception as e:
            self.logger.error(
                "deepinfra_scoring_failed", email_id=email.id, error=str(e)
            )
            raise

    def score_email(self, email: Email) -> Tuple[int, float, str]:
        """Score an email using multiple methods and return best result."""
        scores = []
        reasons = []

        # Try AI scoring first
        try:
            priority, confidence, reason = self._score_with_deepinfra(email)
            scores.append((priority, confidence, reason, PrioritySource.DEEP_INFRA))
        except Exception as e:
            self.logger.warning("ai_scoring_failed", email_id=email.id, error=str(e))

        # Always do deterministic scoring
        try:
            # Start with default priority
            priority = 1
            confidence = 0.8
            reasons = []

            # Check high priority sources
            for source in self.preferences.get("high_priority_sources", []):
                if any(
                    kw.lower() in email.subject.lower() for kw in source["keywords"]
                ):
                    priority = max(priority, source["min_priority"])
                    reasons.append(source["reason"])
                    confidence = 0.9

            # Check low priority sources
            for source in self.preferences.get("low_priority_sources", []):
                if any(
                    kw.lower() in email.subject.lower() for kw in source["keywords"]
                ):
                    priority = min(priority, source.get("max_priority", 1))
                    reasons.append(source["reason"])
                    confidence = 0.9

            # Apply newsletter defaults
            for newsletter, config in self.preferences.get(
                "newsletter_defaults", {}
            ).items():
                if any(
                    kw.lower() in email.subject.lower() for kw in config["keywords"]
                ):
                    priority = config["default_priority"]
                    reasons.append(config["reason"])
                    confidence = 0.95

            # Check override rules
            for rule in self.preferences.get("override_rules", []):
                if any(kw.lower() in email.subject.lower() for kw in rule["keywords"]):
                    priority = max(priority, rule["min_priority"])
                    reasons.append(rule["reason"])
                    confidence = 0.95

            reason = " | ".join(reasons) if reasons else "Default priority"
            scores.append((priority, confidence, reason, PrioritySource.DETERMINISTIC))

        except Exception as e:
            self.logger.error(
                "deterministic_scoring_failed", email_id=email.id, error=str(e)
            )

        if not scores:
            return 1, 0.5, "Scoring failed"

        # Use result with highest confidence
        priority, confidence, reason, source = max(scores, key=lambda x: x[1])

        # Log edge cases
        if confidence < 0.7:
            self._log_edge_case(
                email, priority, confidence, f"Low confidence ({source})"
            )
        elif len(scores) > 1:
            priorities = [s[0] for s in scores]
            if max(priorities) - min(priorities) > 1:
                self._log_edge_case(
                    email,
                    priority,
                    confidence,
                    f"Priority disagreement between methods",
                )

        return priority, confidence, reason

    def _log_edge_case(
        self, email: Email, priority: int, confidence: float, reason: str
    ) -> None:
        """Log an edge case for analysis."""
        edge_case = {
            "timestamp": timezone.now().isoformat(),
            "type": "potential_misclassification",
            "subject": email.subject,
            "priority": priority,
            "confidence": confidence,
            "reason": reason,
        }

        # Log to edge cases file
        try:
            edge_cases = self._load_json("edge_cases.json")
            edge_cases.append(edge_case)

            with open(self.config_dir / "edge_cases.json", "w") as f:
                json.dump(edge_cases, f, indent=2)

        except Exception as e:
            self.logger.error(
                "edge_case_logging_failed", error=str(e), error_type=type(e).__name__
            )

        # Create event log
        EventLog.objects.create(
            event_type="PRIORITY_EDGE_CASE",
            email=email,
            details=edge_case,
            performed_by="email_prioritizer",
        )
