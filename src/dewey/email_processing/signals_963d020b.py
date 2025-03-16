# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:39:31 2025

"""Email processing signal handlers."""

import structlog

logger = structlog.get_logger(__name__)

# We'll implement our own message handling without django-mailbox
# This file is kept as a placeholder for future signal handlers
