"""Email processing signal handlers."""

import structlog

logger = structlog.get_logger(__name__)

# We'll implement our own message handling without django-mailbox
# This file is kept as a placeholder for future signal handlers
