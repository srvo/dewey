"""Centralized email prioritization rules and logic."""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re
import structlog
from django.db import connection
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class PriorityRule(BaseModel):
    """Rule for determining email priority."""

    name: str
    pattern_type: str  # regex, simple_match, domain, etc.
    pattern: str
    priority: int = Field(ge=0, le=4)
    category: str
    requires_response: bool = False
    override_llm: bool = True  # Whether this rule overrides LLM decisions


class EmailPriorities:
    """Core email priority determination logic."""

    def __init__(self):
        """Initialize priority rules."""
        # High priority patterns (non-client)
        self.high_priority_rules = [
            PriorityRule(
                name="key_contacts",
                pattern_type="email",
                pattern=r"(tom\.brakke@|joachim\.klement@)",
                priority=4,
                category="key_contact",
                requires_response=True,
            ),
            PriorityRule(
                name="form_submission",
                pattern_type="subject",
                pattern=r"form submission|contact request",
                priority=3,
                category="lead",
                requires_response=True,
            ),
        ]

        # Low priority patterns
        self.low_priority_rules = [
            PriorityRule(
                name="newsletter",
                pattern_type="subject",
                pattern=r"newsletter|digest|weekly update",
                priority=0,
                category="newsletter",
            ),
            PriorityRule(
                name="marketing",
                pattern_type="domain",
                pattern=r"@(mailchimp|sendgrid|hubspot)\.",
                priority=0,
                category="marketing",
            ),
            PriorityRule(
                name="notifications",
                pattern_type="email",
                pattern=r"noreply@|notifications@|updates@",
                priority=1,
                category="notification",
            ),
        ]

        # Special handling rules
        self.special_rules = [
            PriorityRule(
                name="security_alert",
                pattern_type="subject",
                pattern=r"security|alert|warning|critical",
                priority=4,
                category="security",
                requires_response=False,
            ),
            PriorityRule(
                name="calendar",
                pattern_type="subject",
                pattern=r"invitation:|accepted:|declined:|updated:",
                priority=2,
                category="calendar",
                requires_response=False,
            ),
        ]

    def _check_client(self, email: Dict[str, Any]) -> Optional[Tuple[int, str, bool]]:
        """Check if email is from a client using database lookup.

        Args:
            email: Email metadata to check

        Returns:
            Tuple of (priority, category, requires_response) if matched
        """
        try:
            with connection.cursor() as cursor:
                # Check domain matches
                domain = email["from_address"].split("@")[-1]
                cursor.execute(
                    """
                    SELECT id, priority_override 
                    FROM clients 
                    WHERE is_active = true
                    AND (
                        %s = ANY(domains)
                        OR EXISTS (
                            SELECT 1 
                            FROM unnest(email_patterns) pattern 
                            WHERE %s ~ pattern
                        )
                    )
                    LIMIT 1
                """,
                    [domain, email["from_address"]],
                )

                result = cursor.fetchone()
                if result:
                    client_id, priority_override = result
                    return (
                        priority_override if priority_override is not None else 4,
                        "client",
                        True,
                    )

        except Exception as e:
            logger.error("Error checking client status", error=str(e))

        return None

    def _check_rule(
        self, rule: PriorityRule, email: Dict[str, Any]
    ) -> Optional[Tuple[int, str, bool]]:
        """Check if an email matches a priority rule.

        Args:
            rule: Priority rule to check
            email: Email data to check against

        Returns:
            Tuple of (priority, category, requires_response) if matched
        """
        pattern = re.compile(rule.pattern, re.IGNORECASE)

        if rule.pattern_type == "domain":
            if pattern.search(email["from_address"]):
                return rule.priority, rule.category, rule.requires_response

        elif rule.pattern_type == "email":
            if pattern.search(email["from_address"]):
                return rule.priority, rule.category, rule.requires_response

        elif rule.pattern_type == "subject":
            if pattern.search(email["subject"]):
                return rule.priority, rule.category, rule.requires_response

        return None

    def determine_priority(
        self, metadata: Dict[str, Any], content: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Determine email priority using rules.

        Args:
            metadata: Email metadata
            content: Optional email content

        Returns:
            Priority determination including:
            - priority: 0-4 priority level
            - category: Email category
            - requires_response: Whether response is needed
            - confidence: Confidence in determination
            - rule_matched: Name of matched rule if any
            - needs_llm: Whether LLM analysis is needed
        """
        # Check client status first
        if result := self._check_client(metadata):
            priority, category, requires_response = result
            return {
                "priority": priority,
                "category": category,
                "requires_response": requires_response,
                "confidence": 1.0,
                "rule_matched": "client_lookup",
                "needs_llm": False,  # Always trust client detection
            }

        # Check high priority rules
        for rule in self.high_priority_rules:
            if result := self._check_rule(rule, metadata):
                priority, category, requires_response = result
                return {
                    "priority": priority,
                    "category": category,
                    "requires_response": requires_response,
                    "confidence": 1.0,
                    "rule_matched": rule.name,
                    "needs_llm": not rule.override_llm,
                }

        # Check special handling rules
        for rule in self.special_rules:
            if result := self._check_rule(rule, metadata):
                priority, category, requires_response = result
                return {
                    "priority": priority,
                    "category": category,
                    "requires_response": requires_response,
                    "confidence": 1.0,
                    "rule_matched": rule.name,
                    "needs_llm": not rule.override_llm,
                }

        # Check low priority rules
        for rule in self.low_priority_rules:
            if result := self._check_rule(rule, metadata):
                priority, category, requires_response = result
                return {
                    "priority": priority,
                    "category": category,
                    "requires_response": requires_response,
                    "confidence": 1.0,
                    "rule_matched": rule.name,
                    "needs_llm": not rule.override_llm,
                }

        # No rules matched - needs LLM analysis
        return {
            "priority": 2,  # Default to medium priority
            "category": "unknown",
            "requires_response": False,
            "confidence": 0.0,
            "rule_matched": None,
            "needs_llm": True,
        }

    def should_skip_llm(self, priority_result: Dict[str, Any]) -> bool:
        """Determine if LLM analysis can be skipped.

        Args:
            priority_result: Result from determine_priority

        Returns:
            Whether to skip LLM analysis
        """
        return priority_result["confidence"] >= 0.9 and not priority_result["needs_llm"]
