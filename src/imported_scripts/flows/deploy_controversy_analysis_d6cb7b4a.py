from controversy_analysis import analyze_entity_controversies


def deploy_controversy_analysis() -> None:
    """Deploy the controversy analysis flow with a daily schedule."""
    analyze_entity_controversies.serve(
        name="daily-controversy-analysis",
        version="1.0.0",
        cron="0 0 * * *",  # Run daily at midnight UTC
        tags=["controversy", "analysis"],
        description="Daily analysis of entity controversies using SearXNG and Farfalle",
    )


if __name__ == "__main__":
    deploy_controversy_analysis()
