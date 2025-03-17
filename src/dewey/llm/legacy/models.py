
# Refactored from: models
# Date: 2025-03-16T16:19:10.013671
# Refactor Version: 1.0
from django.db import models
from django.urls import reverse


class Page(models.Model):
    """A model representing a static page.

    Attributes:
        title (CharField): The title of the page (max 200 chars)
        slug (SlugField): Unique URL-friendly identifier for the page
        content (TextField): The main content of the page
        created_at (DateTimeField): Timestamp when page was created
        updated_at (DateTimeField): Timestamp when page was last updated

    """

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Metadata options for the Page model.

        Attributes:
            app_label (str): Specifies the app label as 'pages'
            ordering (list): Default ordering by title

        """

        app_label = "pages"
        ordering = ["title"]

    def __str__(self) -> str:
        """String representation of the Page model.

        Returns:
            str: The page title

        """
        return self.title

    def get_absolute_url(self) -> str:
        """Get the canonical URL for this page.

        Uses Django's reverse() to generate URL from URL pattern name.

        Returns:
            str: The absolute URL for this page

        """
        return reverse("pages:page", kwargs={"slug": self.slug})
