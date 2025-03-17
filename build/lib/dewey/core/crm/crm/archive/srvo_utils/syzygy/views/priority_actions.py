"""High-priority actions dashboard with PydanticAI-powered responses."""

from typing import Dict, List
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.db import transaction
from pydantic import BaseModel, Field
from pydantic.ai import ai_fn

from email_processing.prioritization.models import EnrichmentTask
from .base import SyzygyBaseView
import structlog

logger = structlog.get_logger(__name__)


class ActionResponse(BaseModel):
    """Response model for action processing."""

    action_type: str = Field(..., description="Type of action processed")
    response: str = Field(..., description="Generated response text")
    next_steps: List[str] = Field(
        default_factory=list, description="Suggested next steps"
    )
    confidence: float = Field(..., description="Confidence in the response (0-1)")


@ai_fn(
    description="""
Generate a response for a high-priority action.

Instructions:
1. Analyze the action type and context
2. Consider user preferences and history
3. Generate appropriate responses for:
   - Contact merge decisions
   - Email prioritization reviews
   - Contact categorization updates
4. Provide clear reasoning for decisions
5. Format response appropriately for action type
"""
)
def generate_action_response(action_data: Dict) -> ActionResponse:
    pass  # PydanticAI will implement this


@ai_fn(
    description="""
Evaluate and potentially reprioritize an action.

Instructions:
1. Analyze action context and history
2. Consider:
   - Time sensitivity
   - Business impact
   - User preferences
   - Related actions
3. Recommend new priority level
4. Provide clear reasoning for change
"""
)
def reprioritize_action(action_data: Dict, current_priority: str) -> Dict[str, str]:
    pass  # PydanticAI will implement this


@ai_fn
def process_dictation(dictation: str, task_data: Dict) -> Dict[str, str]:
    """Process dictated instructions for a task.

    Instructions:
    1. Analyze the dictated text for:
       - Priority adjustments
       - Task modifications
       - Additional context or notes
    2. Match the user's writing style and tone
    3. Extract key actions and decisions
    4. Format response to update task appropriately
    """
    pass  # Marvin will implement this


class PriorityActionsView(SyzygyBaseView):
    """Dashboard for high-priority actions requiring attention."""

    template_name = "syzygy/priority_actions/dashboard.html"

    def get_context_data(self, **kwargs):
        """Get all high-priority actions."""
        context = super().get_context_data(**kwargs)

        # Get pending merge reviews with high confidence
        merge_reviews = EnrichmentTask.objects.filter(
            task_type="merge_review",
            status="pending",
            metadata__decision__confidence__gte=0.8,
        ).order_by("-created_at")[:5]

        # Get other high-priority tasks
        other_tasks = (
            EnrichmentTask.objects.filter(status="pending", metadata__priority="high")
            .exclude(task_type="merge_review")
            .order_by("-created_at")[:5]
        )

        context.update({"merge_reviews": merge_reviews, "other_tasks": other_tasks})

        return context

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        """Handle action responses."""
        action_id = request.POST.get("action_id")
        action_type = request.POST.get("action_type")
        response_type = request.POST.get("response_type")

        try:
            with transaction.atomic():
                task = EnrichmentTask.objects.get(id=action_id)

                if response_type == "marvin":
                    # Handle dictation if provided
                    dictation = request.POST.get("dictation")
                    if dictation:
                        response = process_dictation(
                            dictation=dictation,
                            task_data={
                                "type": action_type,
                                "task": task.metadata,
                                "history": self._get_action_history(task),
                            },
                        )
                    else:
                        # Regular Marvin response
                        response = generate_action_response(
                            {
                                "type": action_type,
                                "task": task.metadata,
                                "history": self._get_action_history(task),
                            }
                        )

                    # Apply response
                    self._apply_action_response(task, response)

                    return JsonResponse({"status": "success", "response": response})

                elif response_type == "reprioritize":
                    # Handle quick priority downgrade
                    priority = request.POST.get("priority")
                    reason = request.POST.get("reason")

                    if priority and reason:
                        result = {"priority": priority, "reason": reason}
                    else:
                        # Get Marvin's reprioritization decision
                        result = reprioritize_action(
                            action_data=task.metadata,
                            current_priority=task.metadata.get("priority", "normal"),
                        )

                    # Update task priority
                    task.metadata["priority"] = result["priority"]
                    task.metadata["priority_reason"] = result["reason"]
                    task.save()

                    return JsonResponse({"status": "success", "result": result})

                else:
                    return JsonResponse(
                        {"status": "error", "message": "Invalid response type"},
                        status=400,
                    )

        except EnrichmentTask.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Task not found"}, status=404
            )

        except Exception as e:
            logger.error(
                "action_response_failed",
                action_id=action_id,
                error=str(e),
                exc_info=True,
            )
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    def _get_action_history(self, task: EnrichmentTask) -> List[Dict]:
        """Get relevant history for an action."""
        return (
            EnrichmentTask.objects.filter(
                entity_type=task.entity_type, entity_id=task.entity_id
            )
            .exclude(id=task.id)
            .order_by("-created_at")
            .values("task_type", "status", "result", "created_at")[:5]
        )

    def _apply_action_response(self, task: EnrichmentTask, response: Dict):
        """Apply a Marvin-generated response to a task."""
        if response.get("action") == "complete":
            task.status = "completed"
            task.result = {
                "action": "completed",
                "response": response.get("response"),
                "reason": response.get("reason"),
                "generated_by": "marvin",
            }
        elif response.get("action") == "defer":
            task.status = "deferred"
            task.result = {
                "action": "deferred",
                "response": response.get("response"),
                "reason": response.get("reason"),
                "generated_by": "marvin",
            }
        else:
            task.metadata["marvin_response"] = response

        task.save()
