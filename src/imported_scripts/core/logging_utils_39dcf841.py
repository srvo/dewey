import json
from datetime import datetime
from pathlib import Path

import httpx
from posting import Posting, RequestModel


def setup(posting: Posting) -> None:
    """Initialize logging for the request."""
    # Get API name from the request path
    api_name = posting.get_variable("API_NAME", "unknown")

    # Create logs directory if it doesn't exist
    log_dir = Path.home() / "rawls" / "logs" / api_name
    log_dir.mkdir(parents=True, exist_ok=True)

    # Set log file path as a variable
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    posting.set_variable("log_file", str(log_dir / f"{timestamp}.json"))


def on_request(request: RequestModel, posting: Posting) -> None:
    """Log the request details."""
    # Extract API name from URL
    api_name = request.url.host or "unknown"
    posting.set_variable("API_NAME", api_name)

    # Get or create log file
    log_file = posting.get_variable("log_file")
    if not log_file:
        setup(posting)
        log_file = posting.get_variable("log_file")

    # Create log entry
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "api": api_name,
        "request": {
            "url": str(request.url),
            "method": request.method,
            "headers": {h.name: h.value for h in request.headers},
            "query_params": dict(request.params) if request.params else None,
            "body": json.loads(request.content) if request.content else None,
        },
    }

    # Save log
    with open(log_file, "w") as f:
        json.dump(log_entry, f, indent=2)

    posting.notify(f"Request logged: {api_name}", severity="information")


def on_response(response: httpx.Response, posting: Posting) -> None:
    """Log the response details."""
    log_file = posting.get_variable("log_file")
    if not log_file:
        return

    # Load existing log
    with open(log_file) as f:
        log_entry = json.load(f)

    # Parse response body based on content type
    try:
        if response.headers.get("content-type", "").startswith("application/json"):
            response_body = response.json()
        else:
            response_body = response.text
    except Exception as e:
        response_body = f"Error parsing response: {e!s}"

    # Update log with response
    log_entry.update(
        {
            "response": {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body,
                "elapsed": str(response.elapsed),
            },
        },
    )

    # Save updated log
    with open(log_file, "w") as f:
        json.dump(log_entry, f, indent=2)

    # Handle specific API responses
    if "task_id" in str(response_body):
        task_id = response_body.get("task_id")
        if task_id:
            posting.set_variable("TASK_ID", task_id)
            posting.notify(f"Task ID captured: {task_id}", severity="information")

    # Notify based on status code
    if response.status_code >= 400:
        posting.notify(f"Error {response.status_code}", severity="error")
    elif response.status_code >= 300:
        posting.notify(f"Redirect {response.status_code}", severity="warning")
    else:
        posting.notify(f"Success {response.status_code}", severity="success")
