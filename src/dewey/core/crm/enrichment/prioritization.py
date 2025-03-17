"""Email prioritization service for the Dewey CRM system.

This module provides functionality to prioritize emails based on:
1. AI analysis using DeepInfra API
2. Deterministic rules based on user preferences
3. Edge case detection and handling

The prioritization system is designed to be:
- Reliable: Uses retry mechanisms for API calls
- Configurable: Loads preferences from JSON files
- Extensible: Supports multiple prioritization methods
- Auditable: Logs edge cases and decision rationale
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

import requests
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.dewey.core.db import get_duckdb_connection

logger = structlog.get_logger(__name__)


class PrioritySource(Enum):
    """Enum representing different sources of priority decisions."""

    DEEP_INFRA = "deep_infra"
    DETERMINISTIC = "deterministic"
    MANUAL = "manual"


class EmailPrioritizer:
    """Service for scoring and prioritizing emails based on user preferences."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """Initialize the prioritizer with configuration.
        
        Args:
            config_dir: Directory containing configuration files.
                        If None, uses the default config directory.
        """
        self.config_dir = config_dir or Path(os.path.expanduser("~/dewey/config/email"))
        os.makedirs(self.config_dir, exist_ok=True)
        
        self.preferences = self._load_json("email_preferences.json")
        self.edge_cases_file = self.config_dir / "edge_cases.json"
        self.logger = logger.bind(service="email_prioritizer")

    def _load_json(self, filename: str) -> Dict:
        """Load a JSON configuration file.

        Args:
            filename: The name of the JSON file to load.

        Returns:
            A dictionary containing the JSON data. Returns an empty dictionary if loading fails.
        """
        try:
            file_path = self.config_dir / filename
            if file_path.exists():
                with open(file_path) as f:
                    return json.load(f)
            else:
                self.logger.warning(
                    "config_file_not_found",
                    filename=filename,
                    path=str(file_path),
                )
                # Create default config if it doesn't exist
                if filename == "email_preferences.json":
                    default_config = {
                        "high_priority_sources": [
                            {
                                "keywords": ["urgent", "important", "asap"],
                                "min_priority": 4,
                                "reason": "Contains urgency keywords"
                            }
                        ],
                        "low_priority_sources": [
                            {
                                "keywords": ["newsletter", "unsubscribe", "marketing"],
                                "max_priority": 1,
                                "reason": "Marketing or newsletter content"
                            }
                        ],
                        "newsletter_defaults": {},
                        "override_rules": []
                    }
                    with open(file_path, 'w') as f:
                        json.dump(default_config, f, indent=2)
                    return default_config
                return {}
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
    def _score_with_deepinfra(self, email_data: Dict[str, Any]) -> Tuple[int, float, str]:
        """Score email using DeepInfra API with retry logic.

        Args:
            email_data: Dictionary containing email data with at least 'subject' and 'plain_body' keys

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

        subject = email_data.get("subject", "")
        body = email_data.get("plain_body", "")
        content = f"Subject: {subject}\n\n{body}"

        try:
            response = requests.post(
                "https://api.deepinfra.com/v1/openai/chat/completions",
                headers=headers,
                json={
                    "model": "openchat/openchat_3.5",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert at analyzing email importance. "
                                      "Analyze the email and return a JSON object with: "
                                      "priority (0-4, where 4 is highest), confidence (0.0-1.0), "
                                      "and reason (brief explanation)."
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
                email_id=email_data.get("id", "unknown"),
                error=str(e),
            )
            raise

    def _deterministic_score(self, email_data: Dict[str, Any]) -> Tuple[int, float, str]:
        """Score an email based on predefined rules.

        Args:
            email_data: Dictionary containing email data with at least 'subject' and 'plain_body' keys

        Returns:
            A tuple containing the priority, confidence, and reason for the score.
        """
        priority = 1
        confidence = 0.8
        reasons: List[str] = []

        subject = email_data.get("subject", "")
        body = email_data.get("plain_body", "")
        content = f"{subject}\n\n{body}"

        for source in self.preferences.get("high_priority_sources", []):
            if any(kw.lower() in content.lower() for kw in source["keywords"]):
                priority = max(priority, source["min_priority"])
                reasons.append(source["reason"])
                confidence = 0.9

        for source in self.preferences.get("low_priority_sources", []):
            if any(kw.lower() in content.lower() for kw in source["keywords"]):
                priority = min(priority, source.get("max_priority", 1))
                reasons.append(source["reason"])
                confidence = 0.9

        for config in self.preferences.get(
            "newsletter_defaults",
            {},
        ).values():
            if any(kw.lower() in content.lower() for kw in config["keywords"]):
                priority = config["default_priority"]
                reasons.append(config["reason"])
                confidence = 0.95

        for rule in self.preferences.get("override_rules", []):
            if any(kw.lower() in content.lower() for kw in rule["keywords"]):
                priority = max(priority, rule["min_priority"])
                reasons.append(rule["reason"])
                confidence = 0.95

        reason = " | ".join(reasons) if reasons else "Default priority"
        return priority, confidence, reason

    def score_email(self, email_data: Dict[str, Any]) -> Tuple[int, float, str]:
        """Score an email using multiple methods and return the best result.

        Args:
            email_data: Dictionary containing email data with at least 'subject' and 'plain_body' keys

        Returns:
            A tuple containing the priority, confidence, and reason for the score.
        """
        scores: List[Tuple[int, float, str, PrioritySource]] = []

        try:
            priority, confidence, reason = self._score_with_deepinfra(email_data)
            scores.append((priority, confidence, reason, PrioritySource.DEEP_INFRA))
        except Exception as e:
            self.logger.warning("ai_scoring_failed", email_id=email_data.get("id", "unknown"), error=str(e))

        try:
            priority, confidence, reason = self._deterministic_score(email_data)
            scores.append((priority, confidence, reason, PrioritySource.DETERMINISTIC))
        except Exception as e:
            self.logger.exception(
                "deterministic_scoring_failed",
                email_id=email_data.get("id", "unknown"),
                error=str(e),
            )

        if not scores:
            return 1, 0.5, "Scoring failed"

        # Get the score with the highest confidence
        priority, confidence, reason, source = max(scores, key=lambda x: x[1])

        # Log edge cases
        if confidence < 0.7:
            self._log_edge_case(
                email_data,
                priority,
                confidence,
                f"Low confidence ({source.value})",
            )
        elif len(scores) > 1:
            priorities = [s[0] for s in scores]
            if max(priorities) - min(priorities) > 1:
                self._log_edge_case(
                    email_data,
                    priority,
                    confidence,
                    "Priority disagreement between methods",
                )

        return priority, confidence, reason

    def _log_edge_case(
        self,
        email_data: Dict[str, Any],
        priority: int,
        confidence: float,
        reason: str,
    ) -> None:
        """Log an edge case for analysis.

        Args:
            email_data: Dictionary containing email data
            priority: The assigned priority
            confidence: The confidence level of the priority assignment
            reason: The reason for considering this an edge case
        """
        edge_case = {
            "timestamp": datetime.now().isoformat(),
            "type": "potential_misclassification",
            "subject": email_data.get("subject", ""),
            "priority": priority,
            "confidence": confidence,
            "reason": reason,
        }

        try:
            # Load existing edge cases
            edge_cases = []
            if self.edge_cases_file.exists():
                with open(self.edge_cases_file) as f:
                    edge_cases = json.load(f)
            
            # Append new edge case
            edge_cases.append(edge_case)
            
            # Save updated edge cases
            with open(self.edge_cases_file, "w") as f:
                json.dump(edge_cases, f, indent=2)

        except Exception as e:
            self.logger.exception(
                "edge_case_logging_failed",
                error=str(e),
                error_type=type(e).__name__,
            )

        # Log the edge case
        self.logger.warning(
            "priority_edge_case",
            subject=email_data.get("subject", ""),
            priority=priority,
            confidence=confidence,
            reason=reason,
        )

    def store_priority_result(self, email_id: str, priority: int, confidence: float, reason: str) -> bool:
        """Store the priority result in the database.
        
        Args:
            email_id: The ID of the email
            priority: The assigned priority
            confidence: The confidence level
            reason: The reason for the priority assignment
            
        Returns:
            True if the result was stored successfully, False otherwise
        """
        try:
            with get_duckdb_connection() as conn:
                # Check if email_analyses table exists
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS email_analyses (
                        id INTEGER PRIMARY KEY,
                        email_id VARCHAR,
                        analysis_type VARCHAR,
                        priority INTEGER,
                        confidence FLOAT,
                        reason VARCHAR,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(email_id, analysis_type)
                    )
                """)
                
                # Insert or update priority result
                conn.execute("""
                    INSERT OR REPLACE INTO email_analyses (
                        email_id, analysis_type, priority, confidence, reason
                    ) VALUES (?, ?, ?, ?, ?)
                """, (email_id, "priority", priority, confidence, reason))
                
                # Update the email's priority field if it exists
                conn.execute("""
                    UPDATE emails 
                    SET priority = ?, 
                        metadata = json_insert(
                            COALESCE(metadata, '{}'), 
                            '$.priority_confidence', ?,
                            '$.priority_reason', ?,
                            '$.priority_updated_at', ?
                        )
                    WHERE id = ?
                """, (
                    priority, 
                    confidence, 
                    reason, 
                    datetime.now().isoformat(),
                    email_id
                ))
                
                return True
        except Exception as e:
            self.logger.exception(
                "priority_storage_failed",
                email_id=email_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            return False


def prioritize_emails(batch_size: int = 100) -> int:
    """Process a batch of emails for prioritization.
    
    Args:
        batch_size: Number of emails to process in this batch
        
    Returns:
        Number of emails successfully prioritized
    """
    prioritizer = EmailPrioritizer()
    logger.info("Starting email prioritization batch", batch_size=batch_size)
    
    try:
        with get_duckdb_connection() as conn:
            # Get emails that haven't been prioritized yet
            result = conn.execute("""
                SELECT e.id, e.subject, e.plain_body, e.from_email
                FROM emails e
                LEFT JOIN email_analyses a ON e.id = a.email_id AND a.analysis_type = 'priority'
                WHERE a.id IS NULL
                LIMIT ?
            """, (batch_size,)).fetchall()
            
            if not result:
                logger.info("No emails to prioritize")
                return 0
                
            logger.info(f"Found {len(result)} emails to prioritize")
            
            success_count = 0
            for row in result:
                email_id, subject, plain_body, from_email = row
                
                email_data = {
                    "id": email_id,
                    "subject": subject,
                    "plain_body": plain_body,
                    "from_email": from_email
                }
                
                try:
                    priority, confidence, reason = prioritizer.score_email(email_data)
                    if prioritizer.store_priority_result(email_id, priority, confidence, reason):
                        success_count += 1
                        logger.info(
                            "email_prioritized",
                            email_id=email_id,
                            priority=priority,
                            confidence=confidence
                        )
                except Exception as e:
                    logger.exception(
                        "email_prioritization_failed",
                        email_id=email_id,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
            
            logger.info(
                "Completed email prioritization batch",
                processed=len(result),
                successful=success_count
            )
            return success_count
            
    except Exception as e:
        logger.exception(
            "email_prioritization_batch_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Prioritize emails in the database")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of emails to process")
    args = parser.parse_args()
    
    prioritize_emails(args.batch_size) 