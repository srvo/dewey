# Formatting failed: LLM generation failed: Gemini API error: Model gemini-2.0-flash in cooldown until Sat Mar 15 00:47:41 2025

"""Test the email analyzer on sample emails.

This module contains a comprehensive test suite for evaluating the email analyzer's
performance across different email categories and models. It includes:
- Predefined test cases covering various email types (marketing, system notifications, etc.)
- Integration tests for different AI models (Nemo, Mistral, Phi-4)
- Detailed logging of analysis results including scores, metadata, and sender history
- Error handling and reporting for failed analyses

The test cases are designed to validate:
1. Priority classification accuracy
2. Model consistency across different email types
3. Performance metrics (latency)
4. Edge case handling
"""

import logging

from scripts.email_analyzer import EmailAnalyzer, ModelType

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Predefined test cases organized by category
# Each test case includes:
# - id: Unique identifier for the test case
# - from: Sender email address
# - subject: Email subject line
# - content: Email body content
# - expected_priority: Expected classification (low/medium/high)
# - notes: Explanation of test case purpose
TEST_EMAILS = {
    "Marketing & Automation": [
        {
            "id": "marketing_1",
            "from": "messages-noreply@linkedin.com",
            "subject": "Rowena just messaged you",
            "content": """Your InMail from Rowena... [LinkedIn marketing message about bookkeeping services]""",
            "expected_priority": "low",
            "notes": "Standard marketing email, should be low priority",
        },
        {
            "id": "newsletter_1",
            "from": "newsletter@substack.com",
            "subject": "Weekly Investment Insights",
            "content": """This week's market analysis: The Fed's latest move signals a potential shift in monetary policy...""",
            "expected_priority": "medium",
            "notes": "High-value newsletter, should be medium priority",
        },
    ],
    "System Notifications": [
        {
            "id": "system_1",
            "from": "expiry@letsencrypt.org",
            "subject": "Let's Encrypt certificate expiration notice",
            "content": """Hello, Your certificate for ecic-server.ec1c.com will expire in 19 days. Please take action to renew the certificate before it expires to avoid any service interruptions.""",
            "expected_priority": "high",
            "notes": "Critical system notification with deadline",
        },
        {
            "id": "system_2",
            "from": "no-reply@github.com",
            "subject": "Security Alert: Critical vulnerability in one of your dependencies",
            "content": """A critical severity security vulnerability was found in your repository's dependencies. Immediate action recommended.""",
            "expected_priority": "high",
            "notes": "Security alert requiring immediate attention",
        },
    ],
    "Client Communications": [
        {
            "id": "client_1",
            "from": "important.client@company.com",
            "subject": "Re: Project Timeline Update",
            "content": """Thanks for the update. Can we schedule a call tomorrow to discuss the new requirements? This is time-sensitive as we need to present to our board next week.""",
            "expected_priority": "high",
            "notes": "Direct client communication with urgency",
        },
        {
            "id": "client_2",
            "from": "prospect@newclient.com",
            "subject": "Interest in Services",
            "content": """Following our meeting last week, we'd like to move forward with the proposal. Please send over the contract for review.""",
            "expected_priority": "high",
            "notes": "New business opportunity requiring timely response",
        },
    ],
    "Internal Communications": [
        {
            "id": "internal_1",
            "from": "ceo@company.com",
            "subject": "All Hands Meeting Tomorrow",
            "content": """Please join us tomorrow at 10 AM for an important company update. Attendance is mandatory.""",
            "expected_priority": "high",
            "notes": "Internal communication from leadership",
        },
        {
            "id": "internal_2",
            "from": "hr@company.com",
            "subject": "Reminder: Complete Annual Review",
            "content": """This is a reminder to complete your annual performance review by end of week. This is required for the upcoming compensation review.""",
            "expected_priority": "medium",
            "notes": "HR process with deadline but not immediate",
        },
    ],
    "Edge Cases": [
        {
            "id": "edge_1",
            "from": "no-reply@automated-service.com",
            "subject": "Your Account Statement",
            "content": """URGENT: Unusual activity detected in your account. Multiple failed login attempts recorded. Please verify your account security immediately.""",
            "expected_priority": "high",
            "notes": "Automated but security-critical message",
        },
        {
            "id": "edge_2",
            "from": "newsletter@trusted-source.com",
            "subject": "Breaking: Major Market Movement",
            "content": """MARKET ALERT: S&P 500 down 5% in early trading. Major tech stocks seeing significant volatility. Immediate portfolio review recommended.""",
            "expected_priority": "high",
            "notes": "Newsletter but with time-critical information",
        },
    ],
}


def main() -> None:
    """Execute the email analyzer test suite across all supported models.

    This function:
    1. Initializes analyzers for each supported model (Nemo, Mistral, Phi-4)
    2. Iterates through all test categories and individual test cases
    3. Runs analysis on each email using each model
    4. Logs detailed results including:
       - Scores and reasoning
       - Metadata
       - Sender history
       - Analysis latency
    5. Handles and logs any analysis errors

    The output is structured to make it easy to:
    - Compare model performance
    - Identify classification patterns
    - Detect edge case handling issues
    """
    # Initialize analyzers for all supported models
    analyzers = {
        "Nemo": EmailAnalyzer(default_model=ModelType.NEMO),
        "Mistral": EmailAnalyzer(default_model=ModelType.MISTRAL),
        "Phi-4": EmailAnalyzer(default_model=ModelType.PHI4),
    }

    for model_name, analyzer in analyzers.items():
        # Start new model test section
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Testing with {model_name} model:")
        logger.info("=" * 80)

        # Process each email category
        for category, emails in TEST_EMAILS.items():
            logger.info(f"\n{'-' * 40}")
            logger.info(f"Category: {category}")
            logger.info(f"{'-' * 40}")

            # Process each email in the category
            for email in emails:
                logger.info(f"\nAnalyzing email: {email['subject']}")
                logger.info(f"Expected Priority: {email['expected_priority']}")
                logger.info(f"Test Notes: {email['notes']}")

                try:
                    # Run analysis on the email
                    result = analyzer.analyze_email(
                        email_id=email["id"],
                        email_content=email["content"],
                        from_email=email["from"],
                    )

                    # Log detailed analysis results
                    logger.info("\nScores and Reasoning:")
                    for score_type, details in result.scores.items():
                        logger.info(f"\n  {score_type.upper()}:")
                        for key, value in details.items():
                            if isinstance(value, list):
                                logger.info(f"    {key}:")
                                for item in value:
                                    logger.info(f"      - {item}")
                            else:
                                logger.info(f"    {key}: {value}")

                    # Log metadata including model configuration and analysis parameters
                    logger.info("\nMetadata:")
                    for key, value in result.metadata.items():
                        if isinstance(value, list):
                            logger.info(f"  {key}:")
                            for item in value:
                                logger.info(f"    - {item}")
                        else:
                            logger.info(f"  {key}: {value}")

                    # Log sender history to validate history-based prioritization
                    logger.info("\nSender History:")
                    for key, value in result.sender_history.items():
                        logger.info(f"  {key}: {value}")

                    # Log performance metrics
                    logger.info(f"\nAnalysis latency: {result.latency:.2f}s")

                except Exception as e:
                    # Handle and log any analysis errors
                    logger.exception(f"Error analyzing email: {e}")
                    logger.exception(f"Email ID: {email['id']}")
                    logger.exception(f"Model: {model_name}")


if __name__ == "__main__":
    main()
