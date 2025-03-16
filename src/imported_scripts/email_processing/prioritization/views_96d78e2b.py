"""Contact merge review interface views."""

import structlog
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, ListView
from email_processing.prioritization.contact_merger import ContactMerger
from email_processing.prioritization.models import Contact, EnrichmentTask

logger = structlog.get_logger(__name__)


class MergeReviewListView(LoginRequiredMixin, ListView):
    """List view of pending contact merge reviews."""

    template_name = "syzygy/contact_review/merge_list.html"
    context_object_name = "merge_tasks"
    paginate_by = 20

    def get_queryset(self):
        """Get pending merge review tasks."""
        return EnrichmentTask.objects.filter(
            task_type="merge_review",
            status="pending",
        ).order_by("-created_at")

    def get_context_data(self, **kwargs):
        """Add additional context."""
        context = super().get_context_data(**kwargs)

        # Add contact details for each task
        tasks_with_details = []
        for task in context["merge_tasks"]:
            primary_contact = Contact.objects.get(id=task.entity_id)
            candidate_id = task.metadata.get("candidate_id")
            candidate_contact = (
                Contact.objects.get(id=candidate_id) if candidate_id else None
            )

            tasks_with_details.append(
                {
                    "task": task,
                    "primary_contact": primary_contact,
                    "candidate_contact": candidate_contact,
                    "similarity": task.metadata.get("similarity", {}),
                    "decision": task.metadata.get("decision", {}),
                },
            )

        context["tasks_with_details"] = tasks_with_details
        return context


class MergeReviewDetailView(LoginRequiredMixin, DetailView):
    """Detailed view of a merge review task."""

    template_name = "syzygy/contact_review/merge_detail.html"
    model = EnrichmentTask
    context_object_name = "task"

    def get_object(self):
        """Get the task and verify it's a merge review."""
        return get_object_or_404(
            EnrichmentTask,
            id=self.kwargs["task_id"],
            task_type="merge_review",
        )

    def get_context_data(self, **kwargs):
        """Add contact details and enrichment data."""
        context = super().get_context_data(**kwargs)
        task = context["task"]

        # Get contacts
        primary_contact = Contact.objects.get(id=task.entity_id)
        candidate_id = task.metadata.get("candidate_id")
        candidate_contact = (
            Contact.objects.get(id=candidate_id) if candidate_id else None
        )

        # Add to context
        context.update(
            {
                "primary_contact": primary_contact,
                "candidate_contact": candidate_contact,
                "similarity": task.metadata.get("similarity", {}),
                "decision": task.metadata.get("decision", {}),
                "can_auto_merge": task.metadata.get("decision", {}).get("confidence", 0)
                >= 0.7,
            },
        )

        return context

    def post(self, request, *args, **kwargs):
        """Handle merge decisions."""
        task = self.get_object()
        action = request.POST.get("action")

        try:
            with transaction.atomic():
                if action == "merge":
                    # Perform merge
                    merger = ContactMerger()
                    result = merger.merge_contacts(
                        primary_id=task.entity_id,
                        secondary_id=task.metadata["candidate_id"],
                        force=True,
                    )

                    # Update task
                    task.status = "completed"
                    task.result = {
                        "action": "merged",
                        "merge_result": result,
                        "decided_by": request.user.email,
                    }
                    task.save()

                    messages.success(request, "Contacts successfully merged")

                elif action == "reject":
                    # Update task
                    task.status = "completed"
                    task.result = {
                        "action": "rejected",
                        "reason": request.POST.get("reject_reason", "Manual rejection"),
                        "decided_by": request.user.email,
                    }
                    task.save()

                    messages.success(request, "Merge rejected")

                elif action == "defer":
                    # Update task
                    task.status = "deferred"
                    task.result = {
                        "action": "deferred",
                        "reason": request.POST.get(
                            "defer_reason",
                            "Needs more information",
                        ),
                        "decided_by": request.user.email,
                    }
                    task.save()

                    messages.info(request, "Review deferred for later")

                else:
                    messages.error(request, "Invalid action")
                    return self.get(request, *args, **kwargs)

        except Exception as e:
            logger.error(
                "merge_review_action_failed",
                task_id=task.id,
                action=action,
                error=str(e),
                exc_info=True,
            )
            messages.error(request, f"Error processing action: {e!s}")
            return self.get(request, *args, **kwargs)

        return redirect("syzygy:merge_review_list")
