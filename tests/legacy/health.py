
# Refactored from: health
# Date: 2025-03-16T16:19:09.533987
# Refactor Version: 1.0
from django.core.cache import cache
from django.db import connections
from django.http import JsonResponse


def health_check(request):
    """Health check endpoint for the application."""
    health_status = {
        "status": "healthy",
        "services": {"database": False, "redis": False},
    }

    # Check database
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health_status["services"]["database"] = True
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["services"]["database"] = str(e)

    # Check Redis
    try:
        cache.set("health_check", "ok", timeout=1)
        assert cache.get("health_check") == "ok"
        health_status["services"]["redis"] = True
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["services"]["redis"] = str(e)

    status_code = 200 if health_status["status"] == "healthy" else 503
    return JsonResponse(health_status, status=status_code)
