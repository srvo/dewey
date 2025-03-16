"""Base views for Syzygy app."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.utils import timezone
from django.views.generic import TemplateView
from email_processing.prioritization.models import Contact, EnrichmentTask
from syzygy.models.timeline import TimelineView


class SyzygyBaseView(LoginRequiredMixin, TemplateView):
    """Base view for Syzygy app that provides common context."""

    def get_context_data(self, **kwargs):
        """Add common context data for sidebar."""
        context = super().get_context_data(**kwargs)

        # Get counts for sidebar badges
        # Get timeline statistics
        timeline_stats = TimelineView.objects.aggregate(
            total_events=Count("id"),
            today_events=Count("id", filter=Q(created_at__date=timezone.now().date())),
            important_events=Count("id", filter=Q(importance_level__gt=0)),
        )

        context.update(
            {
                "contact_count": Contact.objects.count(),
                "email_count": EnrichmentTask.objects.filter(
                    task_type="email_processing",
                ).count(),
                "pending_merges": EnrichmentTask.objects.filter(
                    task_type="merge_review",
                    status="pending",
                ).count(),
                "pending_categories": EnrichmentTask.objects.filter(
                    task_type="categorization",
                    status="pending",
                ).count(),
                "timeline_stats": timeline_stats,
            },
        )

        return context
