"""Deploy controversy monitoring flows to Prefect."""

from controversy_detection import monitor_all_companies


def main() -> None:
    # Deploy the flow with a daily schedule
    monitor_all_companies.deploy(
        name="daily-controversy-monitor",
        work_queue_name="controversy-monitor",
        cron="0 2 * * *",  # Run daily at 2 AM UTC
        tags=["controversy", "monitoring"],
        description="Daily monitoring of company controversies using SearXNG and OpenAI",
    )


if __name__ == "__main__":
    main()
