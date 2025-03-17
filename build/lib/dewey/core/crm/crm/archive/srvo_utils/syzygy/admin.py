"""Admin interface for Syzygy models."""

from django.contrib import admin
from .models import (
    LLMTransaction,
    ToolUsage,
    TimelineView,
    Client,
    Transcript,
    TranscriptAnalysis,
    Activity
)

@admin.register(TimelineView)
class TimelineViewAdmin(admin.ModelAdmin):
    """Admin interface for timeline view."""
    list_display = (
        'created_at',
        'event_type',
        'description',
        'importance_level'
    )
    list_filter = ('event_type', 'importance_level')
    search_fields = ('description', 'metadata')
    readonly_fields = (
        'created_at',
        'event_type',
        'description',
        'metadata',
        'importance_level',
        'related_objects'
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'organization', 'created_at')
    search_fields = ('name', 'email', 'organization')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ('client', 'security', 'interaction_type', 'created_at')
    search_fields = ('content', 'metadata')
    readonly_fields = ('created_at',)

@admin.register(TranscriptAnalysis)
class TranscriptAnalysisAdmin(admin.ModelAdmin):
    list_display = ('transcript', 'sentiment', 'created_at')
    search_fields = ('summary', 'key_points')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('client', 'activity_type', 'created_at')
    search_fields = ('description', 'metadata')
    readonly_fields = ('created_at',)


from django.db import models
from django.utils.html import format_html
from django.apps import AppConfig
from markdownx.widgets import AdminMarkdownxWidget
from markdownx.models import MarkdownxField


class SyzygyConfig(AppConfig):
    """Configuration for Syzygy admin interface."""

    name = "syzygy"
    verbose_name = "Investment Research"

    def ready(self):
        """Initialize app configuration."""
        pass


from .models import (
    Universe,
    ResearchIteration,
    ResearchResults,
    ResearchSources,
    Exclusion,
    TickHistory,
    ResponseDraft,
    tracking,
)


# Register models in desired order
class SyzygyAdminSite(admin.AdminSite):
    """Custom admin site for Syzygy."""

    site_header = "Syzygy Research Platform"
    site_title = "Syzygy Admin"
    index_title = "Research Management"


admin_site = SyzygyAdminSite(name="syzygy_admin")


@admin.register(tracking.LLMTransaction)
class LLMTransactionAdmin(admin.ModelAdmin):
    """Admin interface for LLM transactions."""

    list_display = (
        "created_at",
        "user",
        "model_name",
        "input_tokens",
        "output_tokens",
        "cost",
        "latency_ms",
    )
    list_filter = ("model_name", "user")
    search_fields = ("prompt", "response")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "model_name",
                    "prompt",
                    "response",
                ),
            },
        ),
        (
            "Metrics",
            {
                "fields": (
                    "input_tokens",
                    "output_tokens",
                    "cost",
                    "latency_ms",
                ),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("metadata",),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(tracking.ToolUsage)
class ToolUsageAdmin(admin.ModelAdmin):
    """Admin interface for tool usage tracking."""

    list_display = (
        "created_at",
        "user",
        "tool_name",
        "duration_ms",
        "success",
    )
    list_filter = ("tool_name", "user", "success")
    search_fields = ("parameters", "result")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "user",
                    "tool_name",
                    "parameters",
                    "result",
                ),
            },
        ),
        (
            "Execution",
            {
                "fields": (
                    "duration_ms",
                    "success",
                    "error_message",
                ),
            },
        ),
        (
            "Resources",
            {
                "fields": ("resource_usage",),
                "classes": ("collapse",),
            },
        ),
    )


admin_site = SyzygyAdminSite(name="syzygy_admin")


@admin.register(Universe)
class UniverseAdmin(admin.ModelAdmin):
    """Admin interface for securities in our investment universe."""

    class Meta:
        verbose_name_plural = "Universe"

    list_display = (
        "ticker",
        "name",
        "openfigi",
        "security_type",
        "sector",
        "market_cap",
    )
    list_filter = ("security_type", "sector", "industry")
    search_fields = ("ticker", "name", "openfigi", "isin")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("ticker",)


@admin.register(ResearchIteration)
class ResearchIterationAdmin(admin.ModelAdmin):
    """Admin interface for research iterations."""

    list_display = ("security", "iteration_type", "status", "created_at", "reviewed_by")
    list_filter = ("iteration_type", "status", "reviewed_by")
    search_fields = ("security__ticker", "security__name", "summary")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("security", "previous_iteration")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "security",
                    "iteration_type",
                    "source_count",
                    "date_range",
                    "previous_iteration",
                )
            },
        ),
        (
            "Analysis",
            {
                "fields": (
                    "summary",
                    "key_changes",
                    "risk_factors",
                    "opportunities",
                    "confidence_metrics",
                )
            },
        ),
        (
            "Review",
            {"fields": ("status", "reviewer_notes", "reviewed_by", "reviewed_at")},
        ),
        (
            "Model Info",
            {
                "fields": (
                    "prompt_template",
                    "model_version",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(ResearchResults)
class ResearchResultsAdmin(admin.ModelAdmin):
    """Admin interface for current research results."""

    class Meta:
        verbose_name = "Research Result"
        verbose_name_plural = "Research Results"

    list_display = (
        "security",
        "recommendation",
        "risk_score",
        "confidence_score",
        "last_updated_at",
    )
    list_filter = ("recommendation",)
    search_fields = ("security__ticker", "security__name", "summary")
    readonly_fields = ("first_analyzed_at", "last_updated_at")
    raw_id_fields = ("security", "last_iteration")

    fieldsets = (
        (None, {"fields": ("security", "summary", "recommendation")}),
        ("Scores", {"fields": ("risk_score", "confidence_score")}),
        (
            "Analysis Data",
            {
                "fields": ("structured_data", "raw_results", "search_queries"),
                "classes": ("collapse",),
            },
        ),
        (
            "Sources",
            {"fields": ("source_date_range", "total_sources", "source_categories")},
        ),
        (
            "Tracking",
            {
                "fields": (
                    "last_iteration",
                    "first_analyzed_at",
                    "last_updated_at",
                    "meta_info",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(ResearchSources)
class ResearchSourcesAdmin(admin.ModelAdmin):
    """Admin interface for research sources."""

    class Meta:
        verbose_name = "Research Source"
        verbose_name_plural = "Research Sources"

    list_display = ("security", "title", "source_type", "category", "created_at")
    list_filter = ("source_type", "category")
    search_fields = ("security__ticker", "security__name", "title", "url")
    readonly_fields = ("created_at",)
    raw_id_fields = ("security",)

    def url_link(self, obj):
        """Format URL as clickable link."""
        return format_html('<a href="{}" target="_blank">{}</a>', obj.url, obj.url)

    url_link.short_description = "URL"


@admin.register(Exclusion)
class ExclusionAdmin(admin.ModelAdmin):
    """Admin interface for excluded companies."""

    list_display = (
        "security",
        "category",
        "criteria",
        "decision",
        "is_historical",
        "excluded_at",
    )
    list_filter = ("category", "criteria", "decision", "is_historical")
    search_fields = ("security__ticker", "security__name", "notes")
    readonly_fields = ("excluded_at",)
    raw_id_fields = ("security",)


@admin.register(TickHistory)
class TickHistoryAdmin(admin.ModelAdmin):
    """Admin interface for tick history."""

    class Meta:
        verbose_name = "Tick History"
        verbose_name_plural = "Tick History"

    list_display = ("security", "date", "old_tick", "new_tick", "updated_by")
    list_filter = ("updated_by",)
    search_fields = ("security__ticker", "security__name", "note")
    readonly_fields = ("date",)
    raw_id_fields = ("security",)
    ordering = ("-date",)


@admin.register(ResponseDraft)
class ResponseDraftAdmin(admin.ModelAdmin):
    """Admin interface for email response drafts."""

    list_display = (
        "email_subject",
        "client",
        "status",
        "priority",
        "created_at",
        "reviewed_by",
    )
    list_filter = ("status", "priority", "reviewed_by")
    search_fields = (
        "email_subject",
        "draft_content",
        "context_notes",
        "client__name",
    )
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "client",
                    "email_subject",
                    "original_email",
                ),
            },
        ),
        (
            "Draft",
            {
                "fields": (
                    "draft_content",
                    "context_notes",
                    "status",
                    "priority",
                ),
            },
        ),
        (
            "Review",
            {
                "fields": (
                    "reviewed_by",
                    "reviewed_at",
                ),
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "metadata",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    formfield_overrides = {
        models.TextField: {"widget": AdminMarkdownxWidget},
    }
