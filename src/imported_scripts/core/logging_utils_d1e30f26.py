import json
from datetime import datetime
from pathlib import Path

import httpx
from posting import Posting, RequestModel


def setup(posting: Posting) -> None:
    # Create logs directory if it doesn't exist
    log_dir = Path.home() / "rawls" / "logs" / "gpt-researcher"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Set log file path as a variable for use in other scripts
    log_file = str(log_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    posting.set_variable("log_file", log_file)
    posting.notify(f"Logging to {log_file}", "GPT Researcher")


def on_request(request: RequestModel, posting: Posting) -> None:
    # Log the request
    log_file = posting.get_variable("log_file")
    if not log_file:
        posting.notify("No log file set", "Error", "error")
        return

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "request": {
            "url": str(request.url),
            "method": request.method,
            "headers": {h.name: h.value for h in request.headers},
            "body": json.loads(request.content) if request.content else None,
        },
    }

    with open(log_file, "w") as f:
        json.dump(log_entry, f, indent=2)

    posting.notify("Request logged", "GPT Researcher")


def on_response(response: httpx.Response, posting: Posting) -> None:
    # Update log with response
    log_file = posting.get_variable("log_file")
    if not log_file:
        posting.notify("No log file set", "Error", "error")
        return

    try:
        with open(log_file) as f:
            log_entry = json.load(f)

        response_body: dict | None = None
        try:
            if response.headers.get("content-type", "").startswith("application/json"):
                response_body = response.json()
            else:
                response_body = {"text": response.text}
        except json.JSONDecodeError:
            response_body = {"error": "Invalid JSON response"}

        log_entry.update(
            {
                "response": {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response_body,
                },
            },
        )

        with open(log_file, "w") as f:
            json.dump(log_entry, f, indent=2)

        # If this is a research request, store the task ID for status checking
        if (
            response.status_code == 200
            and isinstance(response_body, dict)
            and "task_id" in response_body
        ):
            task_id = response_body["task_id"]
            posting.set_variable("TASK_ID", task_id)
            posting.notify(
                f"Research task started with ID: {task_id}",
                "GPT Researcher",
                "information",
                timeout=5.0,
            )
    except Exception as e:
        posting.notify(f"Error logging response: {e!s}", "Error", "error")
