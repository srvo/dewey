# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:28:08 2025

import logging

logger = logging.getLogger(__name__)

def generate_report(data):
    try:
        # existing report generation logic...
    except Exception as e:
        logger.error(f"Failed to generate tick report: {e}")
        raise
