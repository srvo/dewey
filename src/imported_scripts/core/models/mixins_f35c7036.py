from django.db import models
from django.utils import timezone


class AuditMixin(models.Model):
    """Mixin class to add audit trail fields to Django models.

    This mixin adds standard audit fields to track creation, modification,
    and deletion of records. It's designed to be inherited by other models
    to provide consistent audit capabilities across the application.

    The mixin implements the following features:
    - Automatic timestamping of record creation and updates
    - Tracking of user actions (create/update/delete)
    - Support for soft delete tracking
    - Consistent field naming and types across models
    - Abstract base class to prevent direct instantiation

    Usage:
        class MyModel(AuditMixin, models.Model):
            # Model fields here
            pass

    Attributes
    ----------
        created_by (CharField): User who created the record (nullable)
        updated_by (CharField): User who last updated the record (nullable)
        deleted_by (CharField): User who deleted the record (nullable)
        created_at (DateTimeField): Timestamp when record was created (auto)
        updated_at (DateTimeField): Timestamp when record was last updated (auto)

    Methods
    -------
        save(): Overrides default save to handle audit fields

    Meta:
        abstract (bool): Prevents direct instantiation
        verbose_name (str): Human-readable name
        verbose_name_plural (str): Plural name
        ordering (list): Default ordering for queries

    """

    # Track user who created the record
    created_by = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Username or identifier of the user who created this record. "
        "Automatically populated during record creation.",
    )

    # Track user who last modified the record
    updated_by = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Username or identifier of the user who last updated this record. "
        "Automatically updated on each save operation.",
    )

    # Track user who deleted the record (for soft delete scenarios)
    deleted_by = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Username or identifier of the user who deleted this record. "
        "Used in conjunction with soft delete functionality.",
    )

    # Automatic timestamp for record creation
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this record was created. "
        "Automatically set on first save.",
    )

    # Automatic timestamp for last update
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when this record was last updated. "
        "Automatically updated on each save operation.",
    )

    class Meta:
        """Metadata options for the AuditMixin.

        Configures the mixin as an abstract base class and sets default
        ordering and naming conventions.
        """

        abstract = True  # Prevents creation of database table for this model
        verbose_name = "Audit Mixin"  # Human-readable name
        verbose_name_plural = "Audit Mixins"  # Plural name
        ordering = ["-created_at"]  # Default ordering for queries


class SoftDeleteMixin(models.Model):
    """Mixin class to implement soft delete functionality.

    This mixin provides soft delete capabilities by marking records as deleted
    instead of actually removing them from the database. It includes:
    - A deleted_at timestamp field
    - A soft delete method that sets the deleted_at field
    - A hard delete method for actual record removal
    - Integration with Django's delete() method
    - Support for query filtering of deleted records

    The mixin implements the following features:
    - Safe deletion with ability to restore records
    - Timestamp tracking of deletion
    - Custom delete() method override
    - Hard delete capability for permanent removal
    - Abstract base class to prevent direct instantiation

    Usage:
        class MyModel(SoftDeleteMixin, models.Model):
            # Model fields here
            pass

    Attributes
    ----------
        deleted_at (DateTimeField): Timestamp when record was soft deleted (nullable)

    Methods
    -------
        delete(): Overrides default delete to implement soft delete
        hard_delete(): Permanently removes record from database

    Meta:
        abstract (bool): Prevents direct instantiation
        verbose_name (str): Human-readable name
        verbose_name_plural (str): Plural name
        ordering (list): Default ordering for queries

    """

    # Track when record was soft deleted
    deleted_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp when this record was soft deleted. "
        "Null indicates the record is active.",
    )

    def delete(self, using=None, keep_parents=False) -> None:
        """Perform a soft delete by setting the deleted_at timestamp.

        Overrides Django's default delete() method to implement soft delete
        functionality. Instead of removing the record from the database,
        it marks it as deleted by setting the deleted_at timestamp.

        Args:
        ----
            using (str, optional): Database alias to use. Defaults to None.
            keep_parents (bool, optional): Keep parent records. Defaults to False.

        Returns:
        -------
            None

        Example:
        -------
            >>> record.delete()  # Soft delete
            >>> record.deleted_at  # Now contains timestamp

        """
        self.deleted_at = timezone.now()
        self.save(using=using)  # Save with updated deleted_at timestamp

    def hard_delete(self, using=None, keep_parents=False) -> None:
        """Perform a hard (permanent) delete of the record.

        Completely removes the record from the database, bypassing
        the soft delete functionality. Use with caution as this
        operation cannot be undone.

        Args:
        ----
            using (str, optional): Database alias to use. Defaults to None.
            keep_parents (bool, optional): Keep parent records. Defaults to False.

        Returns:
        -------
            None

        Example:
        -------
            >>> record.hard_delete()  # Permanent deletion

        """
        super().delete(using=using, keep_parents=keep_parents)  # Call parent delete

    class Meta:
        """Metadata options for the SoftDeleteMixin.

        Configures the mixin as an abstract base class and sets default
        ordering and naming conventions.
        """

        abstract = True  # Prevents creation of database table for this model
        verbose_name = "Soft Delete Mixin"  # Human-readable name
        verbose_name_plural = "Soft Delete Mixins"  # Plural name
        ordering = ["-deleted_at"]  # Default ordering for queries
