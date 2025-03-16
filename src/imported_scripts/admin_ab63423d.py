"""Admin configuration for database models."""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Contact,
    ContactTag,
    Email,
    EmailContactAssociation,
    EnrichmentTask,
    EventLog,
    RawEmail,
    Tag,
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Admin configuration for Tag model."""

    list_display = ["name", "description", "color", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = [
        (
            None,
            {
                "fields": ["name", "description", "color"],
            },
        ),
        (
            "Timestamps",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]


@admin.register(ContactTag)
class ContactTagAdmin(admin.ModelAdmin):
    """Admin configuration for ContactTag model."""

    list_display = ["contact", "tag", "added_by", "created_at"]
    list_filter = ["tag", "added_by", "created_at"]
    search_fields = [
        "contact__first_name",
        "contact__last_name",
        "contact__primary_email",
        "tag__name",
        "notes",
    ]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = [
        (
            None,
            {
                "fields": ["contact", "tag", "added_by", "notes"],
            },
        ),
        (
            "Timestamps",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]


class ContactTagInline(admin.TabularInline):
    """Inline admin for ContactTag model."""

    model = ContactTag
    extra = 1
    autocomplete_fields = ["tag"]
    fields = ("tag", "notes", "added_by")
    readonly_fields = ("created_at",)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """Admin configuration for Contact model."""

    list_display = (
        "primary_email",
        "first_name",
        "last_name",
        "pronouns",
        "get_tags_display",
        "interaction_count",
        "last_interaction",
    )

    list_filter = (
        "created_at",
        "last_interaction",
        "pronouns",
        "enrichment_status",
    )

    search_fields = ("primary_email", "additional_emails", "first_name", "last_name")

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "primary_email",
                    "additional_emails",
                    "pronouns",
                    "custom_pronouns",
                ),
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "domain",
                    "contact_metadata",
                    "enrichment_status",
                    "confidence_score",
                    "relationship_score",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "History",
            {
                "fields": (
                    "interaction_count",
                    "last_interaction",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "interaction_count",
        "last_interaction",
    )

    inlines = [ContactTagInline]

    def get_tags_display(self, obj):
        """Display tags as colored badges."""
        tags = obj.contacttag_set.select_related("tag").all()
        if not tags:
            return "-"
        return format_html(
            " ".join(
                f'<span style="background-color: {tag.tag.color}; color: white; padding: 2px 6px; border-radius: 3px; margin: 0 2px;">{tag.tag.name}</span>'
                for tag in tags
            ),
        )

    get_tags_display.short_description = "Tags"


@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    """Admin configuration for Email model."""

    list_display = [
        "subject",
        "from_email",
        "from_name",
        "status",
        "processed",
        "importance",
        "category",
        "received_at",
        "processed_date",
    ]

    list_filter = [
        "status",
        "processed",
        "category",
        "importance",
        "is_read",
        "is_starred",
        "created_at",
        "received_at",
    ]

    search_fields = [
        "subject",
        "from_email",
        "from_name",
        "gmail_id",
        "thread_id",
        "to_emails",
        "cc_emails",
        "plain_body",
        "error_message",
    ]

    readonly_fields = [
        "gmail_id",
        "thread_id",
        "history_id",
        "version",
        "processing_version",
        "size_estimate",
        "created_at",
        "updated_at",
        "last_sync_at",
        "processed_date",
    ]

    fieldsets = [
        (
            "Basic Information",
            {
                "fields": [
                    "subject",
                    "snippet",
                    "from_email",
                    "from_name",
                    "to_emails",
                    "cc_emails",
                    "bcc_emails",
                ],
            },
        ),
        (
            "Content",
            {
                "fields": ["plain_body", "html_body", "raw_content"],
                "classes": ["collapse"],
            },
        ),
        (
            "Status & Processing",
            {
                "fields": [
                    "status",
                    "processed",
                    "processing_version",
                    "processed_date",
                    "error_message",
                ],
            },
        ),
        (
            "Gmail Data",
            {
                "fields": [
                    "gmail_id",
                    "thread_id",
                    "history_id",
                    "version",
                    "labels",
                    "category",
                    "importance",
                ],
            },
        ),
        (
            "Flags",
            {
                "fields": [
                    "is_draft",
                    "is_sent",
                    "is_read",
                    "is_starred",
                    "is_trashed",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "Metadata",
            {"fields": ["email_metadata", "size_estimate"], "classes": ["collapse"]},
        ),
        (
            "Timestamps",
            {
                "fields": ["received_at", "created_at", "updated_at", "last_sync_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    def has_add_permission(self, request) -> bool:
        """Disable manual email creation."""
        return False


@admin.register(RawEmail)
class RawEmailAdmin(admin.ModelAdmin):
    """Admin configuration for RawEmail model."""

    list_display = ["gmail_message_id", "thread_id", "history_id", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["gmail_message_id", "thread_id", "history_id"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(EmailContactAssociation)
class EmailContactAssociationAdmin(admin.ModelAdmin):
    """Admin configuration for EmailContactAssociation model."""

    list_display = ["contact", "association_type", "email", "created_at"]
    list_filter = ["association_type", "created_at"]
    search_fields = ["contact__email", "email__subject", "email__gmail_id"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(EventLog)
class EventLogAdmin(admin.ModelAdmin):
    """Admin configuration for EventLog model."""

    list_display = ["event_type", "created_at", "email"]
    list_filter = ["event_type", "created_at"]
    search_fields = ["event_type", "details"]
    readonly_fields = ["created_at"]


@admin.register(EnrichmentTask)
class EnrichmentTaskAdmin(admin.ModelAdmin):
    """Admin configuration for EnrichmentTask model."""

    list_display = (
        "task_type",
        "entity_type",
        "entity_id",
        "status",
        "priority",
        "attempts",
        "next_attempt",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "status",
        "task_type",
        "entity_type",
        "priority",
        "created_at",
        "updated_at",
    )

    search_fields = ("entity_id", "error_message", "created_by", "updated_by")

    readonly_fields = ("id", "created_at", "updated_at", "deleted_at", "attempts")

    fieldsets = (
        (
            "Task Information",
            {
                "fields": (
                    "id",
                    "task_type",
                    "entity_type",
                    "entity_id",
                    "version",
                    "priority",
                ),
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "status",
                    "attempts",
                    "max_attempts",
                    "last_attempt",
                    "next_attempt",
                    "scheduled_for",
                ),
            },
        ),
        ("Results", {"fields": ("result", "error_message", "extra_data")}),
        (
            "Audit",
            {
                "fields": (
                    "created_by",
                    "created_at",
                    "updated_by",
                    "updated_at",
                    "deleted_by",
                    "deleted_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def has_delete_permission(self, request, obj=None) -> bool:
        """Prevent deletion, use soft delete instead."""
        return False

    def get_queryset(self, request):
        """Only show non-deleted tasks by default."""
        qs = super().get_queryset(request)
        return qs.filter(deleted_at__isnull=True)

    actions = ["cancel_tasks", "retry_tasks"]

    def cancel_tasks(self, request, queryset) -> None:
        """Bulk action to cancel selected tasks."""
        for task in queryset:
            task.cancel("Cancelled via admin action")
        self.message_user(request, f"Successfully cancelled {queryset.count()} tasks.")

    cancel_tasks.short_description = "Cancel selected tasks"

    def retry_tasks(self, request, queryset) -> None:
        """Bulk action to retry failed or cancelled tasks."""
        count = 0
        for task in queryset:
            if task.status in ["failed", "cancelled"]:
                task.status = "pending"
                task.next_attempt = None
                task.error_message = ""
                task.save(update_fields=["status", "next_attempt", "error_message"])
                count += 1
        self.message_user(request, f"Successfully queued {count} tasks for retry.")

    retry_tasks.short_description = "Retry selected tasks"
