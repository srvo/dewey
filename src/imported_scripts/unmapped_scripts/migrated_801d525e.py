"""Database migration to add new models and fields for enhanced contact management.

This migration introduces:
- Contact history tracking (ContactHistory)
- Tagging system (Tag, ContactTag)
- Background enrichment tasks (EnrichmentTask)
- Additional fields for contacts and emails
- Indexes for improved query performance

Key Features Added:
1. Versioned contact history tracking
2. Flexible tagging system with notes and metadata
3. Background task management for contact enrichment
4. Enhanced email processing capabilities
5. Improved data organization with indexes
6. Soft delete functionality
7. Relationship scoring and priority tracking
"""

# Standard library imports
import uuid

# Django imports
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Database migration class that implements schema changes.

    This migration builds on previous migration 0005 and adds significant new functionality
    to the contact management system while maintaining data integrity.

    Attributes:
        dependencies: List of previous migrations this one depends on
        operations: List of schema changes to apply

    """

    # This migration depends on the previous contact-related migration
    dependencies = [
        ("database", "0005_alter_contact_options_remove_contact_first_name_and_more"),
    ]

    operations = [
        # Create ContactHistory model for tracking changes to contacts
        migrations.CreateModel(
            name="ContactHistory",
            fields=[
                # UUID primary key for better distribution and uniqueness
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                # Version number for optimistic locking and change tracking
                ("version", models.IntegerField(help_text="Change version number")),
                # Track which fields were modified in this change
                (
                    "changed_fields",
                    models.JSONField(help_text="List of changed field names"),
                ),
                # Store previous values before the change
                ("previous_values", models.JSONField(help_text="Values before change")),
                # Store new values after the change
                ("new_values", models.JSONField(help_text="Values after change")),
                # Type of change being recorded
                (
                    "change_type",
                    models.CharField(
                        choices=[
                            ("create", "Create"),
                            ("update", "Update"),
                            ("delete", "Delete"),
                            ("restore", "Restore"),
                        ],
                        max_length=20,
                    ),
                ),
                # Optional reason for the change
                (
                    "change_reason",
                    models.TextField(blank=True, help_text="Reason for the change"),
                ),
                # Additional metadata about the change
                (
                    "extra_data",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Additional context",
                    ),
                ),
                # Who made the change (user or system)
                (
                    "created_by",
                    models.CharField(
                        help_text="User/system making change",
                        max_length=255,
                    ),
                ),
                # Automatic timestamp of when change occurred
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Contact History",
                "verbose_name_plural": "Contact Histories",
                # Default ordering for querying history
                "ordering": ["-created_at", "-version"],
            },
        ),
        migrations.CreateModel(
            name="ContactTag",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("added_by", models.CharField(default="system", max_length=255)),
                ("notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Contact Tag",
                "verbose_name_plural": "Contact Tags",
            },
        ),
        migrations.CreateModel(
            name="EnrichmentTask",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "entity_type",
                    models.CharField(
                        choices=[
                            ("contact", "Contact"),
                            ("email", "Email"),
                            ("thread", "Thread"),
                        ],
                        max_length=20,
                    ),
                ),
                ("entity_id", models.UUIDField()),
                (
                    "task_type",
                    models.CharField(
                        choices=[
                            ("contact_info", "Contact Information"),
                            ("social_profiles", "Social Profiles"),
                            ("company_info", "Company Information"),
                            ("relationship_score", "Relationship Score"),
                            ("email_analysis", "Email Analysis"),
                            ("custom", "Custom"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "version",
                    models.IntegerField(
                        default=1,
                        help_text="Task version for retries",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("in_progress", "In Progress"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                            ("skipped", "Skipped"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "priority",
                    models.IntegerField(
                        default=0,
                        help_text="Processing priority (higher = more urgent)",
                    ),
                ),
                (
                    "attempts",
                    models.IntegerField(
                        default=0,
                        help_text="Number of processing attempts",
                    ),
                ),
                (
                    "max_attempts",
                    models.IntegerField(
                        default=3,
                        help_text="Maximum allowed attempts",
                    ),
                ),
                ("last_attempt", models.DateTimeField(blank=True, null=True)),
                ("next_attempt", models.DateTimeField(blank=True, null=True)),
                (
                    "scheduled_for",
                    models.DateTimeField(
                        blank=True,
                        help_text="When to process this task",
                        null=True,
                    ),
                ),
                (
                    "result",
                    models.JSONField(
                        blank=True,
                        help_text="Task result data",
                        null=True,
                    ),
                ),
                ("error_message", models.TextField(blank=True)),
                (
                    "extra_data",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Additional task context",
                    ),
                ),
                ("created_by", models.CharField(max_length=255)),
                ("updated_by", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("deleted_by", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "verbose_name": "Enrichment Task",
                "verbose_name_plural": "Enrichment Tasks",
                "ordering": ["-priority", "next_attempt", "created_at"],
            },
        ),
        migrations.CreateModel(
            name="Tag",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=100, unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("color", models.CharField(default="#808080", max_length=7)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Tag",
                "verbose_name_plural": "Tags",
                "ordering": ["name"],
            },
        ),
        migrations.AlterModelOptions(
            name="contact",
            options={
                "ordering": ["last_name", "first_name"],
                "verbose_name": "Contact",
                "verbose_name_plural": "Contacts",
            },
        ),
        migrations.RenameField(
            model_name="contact",
            old_name="email",
            new_name="primary_email",
        ),
        migrations.RemoveField(
            model_name="contact",
            name="name",
        ),
        migrations.AddField(
            model_name="contact",
            name="additional_emails",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="contact",
            name="avg_priority",
            field=models.FloatField(default=0.0, help_text="Calculated priority score"),
        ),
        migrations.AddField(
            model_name="contact",
            name="confidence_score",
            field=models.FloatField(
                default=0.0,
                help_text="Data quality confidence (0.0-1.0)",
            ),
        ),
        migrations.AddField(
            model_name="contact",
            name="custom_pronouns",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="contact",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="contact",
            name="deleted_by",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="contact",
            name="domain",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Email domain for categorization",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="contact",
            name="enrichment_source",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="contact",
            name="enrichment_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("in_progress", "In Progress"),
                    ("completed", "Completed"),
                    ("failed", "Failed"),
                    ("skipped", "Skipped"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="contact",
            name="first_name",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="contact",
            name="last_enriched",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="contact",
            name="last_name",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="contact",
            name="last_priority_change",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="contact",
            name="pronouns",
            field=models.CharField(
                blank=True,
                choices=[
                    ("he/him", "he/him"),
                    ("she/her", "she/her"),
                    ("they/them", "they/them"),
                    ("other", "other"),
                    ("unspecified", "unspecified"),
                ],
                default="unspecified",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="contact",
            name="relationship_score",
            field=models.FloatField(
                default=0.0,
                help_text="Overall relationship strength",
            ),
        ),
        migrations.AddField(
            model_name="contact",
            name="version",
            field=models.IntegerField(
                default=1,
                help_text="Optimistic locking version",
            ),
        ),
        migrations.AddField(
            model_name="email",
            name="bcc_emails",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="email",
            name="category",
            field=models.CharField(
                choices=[
                    ("inbox", "Inbox"),
                    ("sent", "Sent"),
                    ("draft", "Draft"),
                    ("spam", "Spam"),
                    ("trash", "Trash"),
                    ("other", "Other"),
                ],
                db_index=True,
                default="inbox",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="email",
            name="cc_emails",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="email",
            name="error_message",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="email",
            name="from_name",
            field=models.TextField(blank=True, help_text="Sender name"),
        ),
        migrations.AddField(
            model_name="email",
            name="html_body",
            field=models.TextField(blank=True, help_text="HTML content", null=True),
        ),
        migrations.AddField(
            model_name="email",
            name="importance",
            field=models.IntegerField(
                choices=[(0, "Low"), (1, "Normal"), (2, "High"), (3, "Urgent")],
                db_index=True,
                default=1,
            ),
        ),
        migrations.AddField(
            model_name="email",
            name="is_draft",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="email",
            name="is_read",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="email",
            name="is_sent",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="email",
            name="is_starred",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="email",
            name="is_trashed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="email",
            name="plain_body",
            field=models.TextField(
                blank=True,
                help_text="Plain text content",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="email",
            name="processed_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="email",
            name="processing_version",
            field=models.IntegerField(default=1),
        ),
        migrations.AddField(
            model_name="email",
            name="size_estimate",
            field=models.IntegerField(default=0, help_text="Size in bytes"),
        ),
        migrations.AddField(
            model_name="email",
            name="snippet",
            field=models.TextField(blank=True, help_text="Email preview text"),
        ),
        migrations.AddField(
            model_name="email",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "New"),
                    ("processing", "Processing"),
                    ("processed", "Processed"),
                    ("failed", "Failed"),
                    ("ignored", "Ignored"),
                ],
                db_index=True,
                default="new",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="email",
            name="version",
            field=models.IntegerField(default=1, help_text="Processing version"),
        ),
        migrations.AlterField(
            model_name="email",
            name="email_metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddIndex(
            model_name="email",
            index=models.Index(fields=["status", "processed"], name="email_status_idx"),
        ),
        migrations.AddIndex(
            model_name="email",
            index=models.Index(
                fields=["category", "importance"],
                name="email_category_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="email",
            index=models.Index(fields=["from_email"], name="email_sender_idx"),
        ),
        migrations.AddField(
            model_name="contacthistory",
            name="contact",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="history_records",
                to="database.contact",
            ),
        ),
        migrations.AddField(
            model_name="contacttag",
            name="contact",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tag_associations",
                to="database.contact",
            ),
        ),
        migrations.AddIndex(
            model_name="enrichmenttask",
            index=models.Index(
                fields=["entity_type", "entity_id"],
                name="enrichment_entity_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="enrichmenttask",
            index=models.Index(
                fields=["status", "next_attempt"],
                name="enrichment_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="enrichmenttask",
            index=models.Index(
                fields=["task_type", "status"],
                name="enrichment_type_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="enrichmenttask",
            index=models.Index(
                fields=["priority", "status"],
                name="enrichment_priority_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="tag",
            index=models.Index(fields=["name"], name="tag_name_idx"),
        ),
        migrations.AddField(
            model_name="contacttag",
            name="tag",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="contact_associations",
                to="database.tag",
            ),
        ),
        migrations.AddField(
            model_name="contact",
            name="tags",
            field=models.ManyToManyField(
                related_name="contacts",
                through="database.ContactTag",
                to="database.tag",
            ),
        ),
        migrations.AddIndex(
            model_name="contact",
            index=models.Index(
                fields=["primary_email"],
                name="contact_primary_email_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="contact",
            index=models.Index(
                fields=["last_name", "first_name"],
                name="contact_name_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="contact",
            index=models.Index(fields=["domain"], name="contact_domain_idx"),
        ),
        migrations.AddIndex(
            model_name="contact",
            index=models.Index(
                fields=["enrichment_status"],
                name="contact_enrichment_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="contact",
            index=models.Index(
                fields=["relationship_score"],
                name="contact_relationship_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="contacthistory",
            index=models.Index(
                fields=["contact", "version"],
                name="contact_history_version_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="contacthistory",
            index=models.Index(
                fields=["contact", "created_at"],
                name="contact_history_date_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="contacthistory",
            index=models.Index(fields=["change_type"], name="contact_history_type_idx"),
        ),
        migrations.AddIndex(
            model_name="contacttag",
            index=models.Index(fields=["contact", "tag"], name="contact_tag_idx"),
        ),
        migrations.AddIndex(
            model_name="contacttag",
            index=models.Index(fields=["created_at"], name="contact_tag_created_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="contacttag",
            unique_together={("contact", "tag")},
        ),
    ]
