import asyncio
from datetime import datetime
from typing import Any

from prefect import flow, task

# Import the API configuration and database manager
from .api_manager import APIDatabase, api_config


@task
async def check_api_health(api_name: str) -> dict[str, Any]:
    """Check the health of a specific API."""
    config = api_config.get(api_name)
    if not config:
        return {"status": "error", "message": f"API {api_name} not found"}

    try:
        # Implement API-specific health check
        return {
            "status": "healthy",
            "last_check": datetime.now().isoformat(),
            "rate_limit_remaining": config["rate_limit"] - config["queries_made"],
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "last_check": datetime.now().isoformat(),
        }


@task
async def update_usage_stats(db: APIDatabase) -> dict[str, dict[str, int]]:
    """Update and return API usage statistics."""
    return await db.get_usage_stats(days=7)


@task
def check_rate_limits() -> list[dict[str, Any]]:
    """Check rate limits for all APIs."""
    warnings = []
    for api_name, config in api_config.items():
        usage_percent = (config["queries_made"] / config["rate_limit"]) * 100
        if usage_percent > 80:
            warnings.append(
                {
                    "api_name": api_name,
                    "usage_percent": usage_percent,
                    "queries_remaining": config["rate_limit"] - config["queries_made"],
                },
            )
    return warnings


@flow(name="API Manager Flow")
async def api_manager_flow():
    """Main flow for API management."""
    db = APIDatabase()
    await db.ensure_initialized()

    # Check all APIs
    health_checks = []
    for api_name in api_config:
        health = await check_api_health(api_name)
        health_checks.append({api_name: health})

    # Update usage statistics
    usage_stats = await update_usage_stats(db)

    # Check rate limits
    rate_limit_warnings = check_rate_limits()

    # Prepare report
    return {
        "timestamp": datetime.now().isoformat(),
        "health_checks": health_checks,
        "usage_stats": usage_stats,
        "rate_limit_warnings": rate_limit_warnings,
    }

    # Log report


if __name__ == "__main__":
    asyncio.run(api_manager_flow())
