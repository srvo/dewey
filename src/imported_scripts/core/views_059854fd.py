"""Views for the core pages application.

This module contains Django view functions that handle:
- Rendering static pages (home, about)
- Displaying dynamic page content
- Handling 404 errors for missing pages

The views follow Django's best practices for:
- Clean URL routing
- Template rendering
- Error handling
- Context management
"""

from django.shortcuts import get_object_or_404, render

from .models import Page


def home(request):
    """Render the home page.

    This view serves as the main entry point for the website, displaying
    the primary landing page content. It uses the 'pages/home.html' template
    to render the page with standard site navigation and layout.

    Args:
    ----
        request (HttpRequest): The incoming HTTP request containing:
            - User session information
            - Request headers
            - Query parameters
            - POST data (if applicable)

    Returns:
    -------
        HttpResponse: Rendered home page template with:
            - Site-wide context variables
            - Navigation elements
            - Main content area

    Example:
    -------
        >>> response = home(request)
        >>> response.status_code
        200

    """
    return render(request, "pages/home.html")


def about(request):
    """Render the about page.

    This view displays information about the website, organization, or
    application. It uses the 'pages/about.html' template to render
    static content that typically includes:
    - Company/organization information
    - Team member profiles
    - Mission statement
    - Contact information

    Args:
    ----
        request (HttpRequest): The incoming HTTP request

    Returns:
    -------
        HttpResponse: Rendered about page template with:
            - Standard site layout
            - About-specific content
            - Consistent navigation

    Example:
    -------
        >>> response = about(request)
        >>> 'About Us' in response.content
        True

    """
    return render(request, "pages/about.html")


def page_detail(request, slug):
    """Display a specific page by its slug.

    This view handles dynamic page content retrieval and rendering.
    It looks up pages by their unique slug identifier and displays
    the associated content. If no page exists with the given slug,
    a 404 error is raised.

    The view supports:
    - SEO-friendly URLs via slugs
    - Content management through the admin interface
    - Template inheritance for consistent page layouts

    Args:
    ----
        request (HttpRequest): The incoming HTTP request
        slug (str): The unique slug identifier for the page, typically:
            - Lowercase
            - Hyphen-separated
            - URL-friendly

    Returns:
    -------
        HttpResponse: Rendered page detail template with:
            - Page content context
            - Standard site layout
            - Navigation elements

    Raises:
    ------
        Http404: If no page exists with the given slug, indicating:
            - The page was deleted
            - The slug was mistyped
            - The page was never created

    Example:
    -------
        >>> response = page_detail(request, 'about-us')
        >>> response.status_code
        200

    """
    # Retrieve page or raise 404 if not found
    page = get_object_or_404(Page, slug=slug)

    # Render template with page context
    return render(
        request,
        "pages/page_detail.html",
        {
            "page": page,  # Pass the page object to template
        },
    )
