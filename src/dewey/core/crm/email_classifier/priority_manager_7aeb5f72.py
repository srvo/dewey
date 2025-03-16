```python
"""Priority management system for email processing.

Functionality:
- Implements multiple prioritization approaches
- Combines AI analysis with deterministic rules
- Handles edge cases and low-confidence decisions
- Maintains learning from manual corrections

Maintenance Suggestions:
1. Regularly update priority rules
2. Monitor AI model performance
3. Add more sophisticated consensus mechanisms
4. Implement periodic rule reviews

Integration:
- Used by email_operations.py during processing
- Integrated with email_analyzer.py for AI analysis
- Works with gmail_label_learner.py for corrections

Testing:
- Unit tests: tests/test_priority_manager.py
- Test with various email types and priorities
- Verify rule-based prioritization
- Test edge case handling
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from scripts.config import Config

logger = logging.getLogger(__name__)


class PrioritySource(Enum):
    """Enum representing different sources of priority decisions.

    Attributes:
        DEEP_INFRA: Priority determined by DeepInfra AI analysis
        DETERMINISTIC: Priority determined by rule-based system
        LLM: Priority determined by local LLM analysis
        MANUAL: Priority set manually by user intervention
    """

    DEEP_INFRA = "deep_infra"
    DETERMINISTIC = "deterministic"
    LLM = "llm"
    MANUAL = "manual"


@dataclass
class PriorityResult:
    """Dataclass representing the result of a priority calculation.

    Attributes:
        priority: Integer value from 0-5 representing email priority
        confidence: Float from 0-1 representing confidence in the decision
        source: PrioritySource enum indicating how the decision was made
        reason: String explanation of the priority decision
        timestamp: Datetime when the decision was made (defaults to now)

    Note:
        The priority scale is:
        5 - Critical
        4 - High
        3 - Business Operations
        2 - Low
        1 - Very Low
        0 - Marketing/Automated
    """

    priority: int
    confidence: float
    source: PrioritySource
    reason: str
    timestamp: datetime = datetime.now()


class PriorityManager:
    """Central class for managing email prioritization using multiple approaches.

    This class combines AI analysis with deterministic rules to assign priorities
    to incoming emails. It supports multiple prioritization methods and handles
    edge cases and low-confidence decisions.

    Key Features:
    - Integration with DeepInfra API for AI-based prioritization
    - Rule-based prioritization using configurable preferences
    - Edge case detection and logging
    - Multiple prioritization method support
    - Confidence-based decision making

    Usage:
        manager = PriorityManager()
        results = manager.prioritize_email(email_content, from_email, subject)
        final_priority = manager.get_final_priority(results)
    """

    def __init__(self) -> None:
        """Initialize the PriorityManager with configuration and logging."""
        self.config = Config()  # Load application configuration
        self._load_preferences()  # Load prioritization rules and preferences
        self._setup_logging()  # Configure logging for priority decisions

    def _load_preferences(self) -> None:
        """Load prioritization preferences from configuration file.

        The preferences file contains:
        - High priority sources and keywords
        - Low priority sources and keywords
        - Newsletter defaults and configurations
        - Custom rules for specific senders or domains

        If no preferences file is found, initializes with empty preferences
        and logs a warning.
        """
        try:
            with open(self.config.PRIORITY_CONFIG, "r") as f:
                self.preferences = json.load(f)
        except FileNotFoundError:
            logger.warning(
                f"No preferences file found at {self.config.PRIORITY_CONFIG}"
            )
            self.preferences = {}  # Use empty preferences if file not found

    def _setup_logging(self) -> None:
        """Configure logging for priority decisions and edge cases.

        Creates necessary directories for edge case logging and
        initializes the edge_cases_file path from configuration.

        The edge cases file stores:
        - Low confidence decisions
        - Priority disagreements between methods
        - Manual overrides
        - Other exceptional cases for review
        """
        self.edge_cases_file = self.config.EDGE_CASES_FILE
        os.makedirs(
            os.path.dirname(self.edge_cases_file), exist_ok=True
        )  # Ensure directory exists

    def _log_edge_case(self, case_data: Dict) -> None:
        """Log edge cases and priority decisions for future learning.

        Args:
            case_data: Dictionary containing edge case details including:
                      - type: Type of edge case (priority_disagreement, low_confidence)
                      - subject: Email subject
                      - priority: Assigned priority
                      - confidence: Decision confidence
                      - reason: Explanation of decision
                      - source: Method used for decision

        The edge cases are stored in JSONL format (one JSON object per line)
        for easy processing and analysis.
        """
        case_data["timestamp"] = datetime.now().isoformat()  # Add current timestamp
        with open(self.edge_cases_file, "a") as f:
            json.dump(case_data, f)  # Append JSON data
            f.write("\n")  # Newline for JSONL format

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(
            (requests.exceptions.RequestException, ValueError)
        ),
    )
    def _prioritize_with_deepinfra(self, email_content: str) -> PriorityResult:
        """Prioritize email using DeepInfra API with retry logic.

        Args:
            email_content: Full content of the email to analyze

        Returns:
            PriorityResult: Contains priority, confidence, and analysis details

        Raises:
            ValueError: If API key is missing or response is invalid

        The method uses exponential backoff for retries and handles:
        - Network errors
        - API rate limits
        - Invalid responses
        - JSON parsing errors
        """
        api_key = os.getenv("DEEPINFRA_API_KEY")
        if not api_key:
            raise ValueError("DEEPINFRA_API_KEY environment variable not set")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Load system prompt from config file
        with open(self.config.SYSTEM_PROMPTS / "priority.txt", "r") as f:
            system_prompt = f.read()

        # Make API request with timeout and retry logic
        response = requests.post(
            "https://api.deepinfra.com/v1/openai/chat/completions",
            headers=headers,
            json={
                "model": "openchat/openchat_3.5",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Analyze this email:\n{email_content}",
                    },
                ],
                "temperature": 0.1,  # Low temperature for consistent results
                "max_tokens": 100,  # Limit response length
            },
            timeout=10,  # 10 second timeout
        )

        response.raise_for_status()  # Raise HTTP errors

        result = response.json()
        if not result.get("choices"):
            raise ValueError("No choices in API response")

        try:
            # Parse and validate API response
            content = result["choices"][0]["message"]["content"]
            result_json = json.loads(content)
            return PriorityResult(
                priority=result_json["priority"],
                confidence=result_json["confidence"],
                source=PrioritySource.DEEP_INFRA,
                reason=result_json.get("reason", "Deep infra analysis"),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing DeepInfra response: {e}")
            raise ValueError("Invalid response format from DeepInfra API")

    def _prioritize_deterministic(
        self, email_content: str, from_email: str, subject: str
    ) -> PriorityResult:
        """Prioritize email using deterministic rules from preferences.

        Args:
            email_content: Full content of the email
            from_email: Sender's email address
            subject: Email subject line

        Returns:
            PriorityResult: Contains priority, confidence, and decision reason

        The method applies rules in this order:
        1. High priority sources (client communications, critical alerts)
        2. Low priority sources (marketing, newsletters)
        3. Newsletter defaults (specific newsletter handling)
        4. Default case (catch-all for unmatched emails)
        """
        # Check high priority sources first
        for source in self.preferences.get("high_priority_sources", []):
            if any(kw.lower() in email_content.lower() for kw in source["keywords"]):
                return PriorityResult(
                    priority=source["min_priority"],
                    confidence=0.9,
                    source=PrioritySource.DETERMINISTIC,
                    reason=source["reason"],
                )

        # Check low priority sources
        for source in self.preferences.get("low_priority_sources", []):
            if any(kw.lower() in email_content.lower() for kw in source["keywords"]):
                return PriorityResult(
                    priority=source["max_priority"],
                    confidence=0.9,
                    source=PrioritySource.DETERMINISTIC,
                    reason=source["reason"],
                )

        # Check newsletter defaults
        for newsletter, config in self.preferences.get(
            "newsletter_defaults", {}
        ).items():
            if any(kw.lower() in email_content.lower() for kw in config["keywords"]):
                return PriorityResult(
                    priority=config["default_priority"],
                    confidence=0.8,
                    source=PrioritySource.DETERMINISTIC,
                    reason=config["reason"],
                )

        # Default case for emails that don't match any rules
        return PriorityResult(
            priority=2,  # Default to medium-low priority
            confidence=0.6,  # Lower confidence for default case
            source=PrioritySource.DETERMINISTIC,
            reason="Default priority based on no matching rules",
        )

    def prioritize_email(
        self,
        email_content: str,
        from_email: str,
        subject: str,
        methods: Optional[List[PrioritySource]] = None,
    ) -> List[PriorityResult]:
        """Prioritize an email using specified methods.

        Args:
            email_content: Full content of the email to prioritize
            from_email: Sender's email address
            subject: Email subject line
            methods: List of prioritization methods to use. Defaults to:
                    [PrioritySource.DEEP_INFRA, PrioritySource.DETERMINISTIC]

        Returns:
            List[PriorityResult]: Results from each prioritization method

        The method:
        1. Runs each specified prioritization method
        2. Logs edge cases and low-confidence decisions
        3. Returns results from all methods for consensus analysis

        Example:
            results = manager.prioritize_email(
                email_content="...",
                from_email="client@example.com",
                subject="Important Update"
            )
        """
        if methods is None:
            methods = [PrioritySource.DEEP_INFRA, PrioritySource.DETERMINISTIC]

        results = []

        for method in methods:
            try:
                if method == PrioritySource.DEEP_INFRA:
                    result = self._prioritize_with_deepinfra(email_content)
                elif method == PrioritySource.DETERMINISTIC:
                    result = self._prioritize_deterministic(
                        email_content, from_email, subject
                    )
                else:
                    logger.warning(f"Unsupported priority method: {method}")
                    continue

                results.append(result)

                # Log edge cases
                if result.confidence < 0.7 or (
                    len(results) > 1
                    and abs(results[-1].priority - results[-2].priority) > 1
                ):
                    self._log_edge_case(
                        {
                            "type": (
                                "priority_disagreement"
                                if len(results) > 1
                                else "low_confidence"
                            ),
                            "subject": subject,
                            "priority": result.priority,
                            "confidence": result.confidence,
                            "reason": result.reason,
                            "source": result.source.value,
                        }
                    )

            except Exception as e:
                logger.error(f"Error in {method} prioritization: {e}")
                continue

        return results

    def get_final_priority(self, results: List[PriorityResult]) -> PriorityResult:
        """Determine final priority from multiple prioritization results.

        Args:
            results: List of PriorityResult objects from different methods

        Returns:
            PriorityResult: Final priority decision

        Note:
            Currently uses the result with highest confidence, but could be
            enhanced with:
            - Weighted averaging
            - Consensus algorithms
            - Manual override capability
            - Historical accuracy weighting

        The method ensures at least a default priority is returned even if
        no valid results are provided.
        """
        if not results:
            return PriorityResult(
                priority=2,
                confidence=0.5,
                source=PrioritySource.DETERMINISTIC,
                reason="No valid priority results",
            )

        # Use result with highest confidence
        return max(results, key=lambda x: x.confidence)
```
