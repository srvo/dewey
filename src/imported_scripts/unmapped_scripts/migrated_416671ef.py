from agent_analysis import analyze_entity_with_agent


def deploy_agent_analysis() -> None:
    """Deploy the agent-based analysis flow with a daily schedule."""
    analyze_entity_with_agent.serve(
        name="daily-agent-analysis",
        version="1.0.0",
        cron="0 0 * * *",  # Run daily at midnight UTC
        tags=["agent", "analysis"],
        description="Daily entity analysis using Farfalle's agent-based search",
    )


if __name__ == "__main__":
    deploy_agent_analysis()
