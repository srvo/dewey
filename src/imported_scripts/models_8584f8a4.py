"""Models for research tracking and company analysis."""

from django.db import models
from django.utils import timezone

from .metrics import AgentInteraction


class Universe(models.Model):
    """Represents a security in our investment universe."""

    id = models.CharField(max_length=26, primary_key=True)
    name = models.CharField(max_length=255)
    ticker = models.CharField(max_length=20, unique=True)
    isin = models.CharField(max_length=12, null=True, blank=True)
    openfigi = models.CharField(
        "OpenFIGI",
        max_length=12,
        unique=True,
        null=True,  # Temporarily allow null
        blank=True,  # Temporarily allow blank
        help_text="OpenFIGI identifier",
    )
    security_type = models.CharField(max_length=50)
    market_cap = models.FloatField(null=True, blank=True)
    sector = models.CharField(max_length=100, null=True, blank=True)
    industry = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "universe"
        verbose_name = "Universe"
        verbose_name_plural = "Universe"
        indexes = [
            models.Index(fields=["ticker"], name="universe_ticker_idx"),
            models.Index(fields=["openfigi"], name="universe_figi_idx"),
            models.Index(fields=["security_type"], name="universe_type_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.ticker} - {self.name}"


class ResearchIteration(models.Model):
    """Represents a single research iteration for a security."""

    id = models.CharField(max_length=26, primary_key=True)
    security = models.ForeignKey(Universe, on_delete=models.CASCADE)
    iteration_type = models.CharField(max_length=50)
    source_count = models.IntegerField(null=True)
    date_range = models.CharField(max_length=50)
    previous_iteration = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    # Analysis outputs
    summary = models.TextField()
    key_changes = models.JSONField(default=dict)
    risk_factors = models.JSONField(default=dict)
    opportunities = models.JSONField(default=dict)
    confidence_metrics = models.JSONField(default=dict)

    # Review status
    status = models.CharField(max_length=50)
    reviewer_notes = models.TextField(blank=True)
    reviewed_by = models.CharField(max_length=255, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Model metadata
    prompt_template = models.CharField(max_length=100)
    model_version = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "research_iterations"
        indexes = [
            models.Index(
                fields=["security", "iteration_type"],
                name="iteration_security_idx",
            ),
            models.Index(fields=["status"], name="iteration_status_idx"),
            models.Index(fields=["created_at"], name="iteration_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.security.ticker} - {self.iteration_type} ({self.created_at})"

    def log_agent_interaction(self, agent_type: str, operation: str, **kwargs):
        """Log an agent interaction for this research iteration."""
        return AgentInteraction.objects.create(
            agent_type=agent_type,
            operation=operation,
            entity_type="research_iteration",
            entity_id=self.id,
            **kwargs,
        )


class ResearchResults(models.Model):
    """Current research results for a security."""

    id = models.CharField(max_length=26, primary_key=True)
    security = models.OneToOneField(Universe, on_delete=models.CASCADE)
    summary = models.TextField()
    risk_score = models.IntegerField()
    confidence_score = models.IntegerField()
    recommendation = models.CharField(max_length=50)

    # Analysis data
    structured_data = models.JSONField(default=dict)
    raw_results = models.JSONField(default=dict)
    search_queries = models.JSONField(default=dict)

    # Source tracking
    source_date_range = models.CharField(max_length=50)
    total_sources = models.IntegerField()
    source_categories = models.JSONField(default=dict)

    # Iteration tracking
    last_iteration = models.ForeignKey(
        ResearchIteration,
        null=True,
        on_delete=models.SET_NULL,
    )
    first_analyzed_at = models.DateTimeField(default=timezone.now)
    last_updated_at = models.DateTimeField(auto_now=True)

    # Additional tracking
    meta_info = models.JSONField(default=dict)

    class Meta:
        db_table = "research_results"
        verbose_name = "Research Result"
        verbose_name_plural = "Research Results"
        indexes = [
            models.Index(fields=["security"], name="results_security_idx"),
            models.Index(
                fields=["risk_score", "confidence_score"],
                name="results_scores_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.security.ticker} - {self.recommendation}"

    def log_agent_interaction(self, agent_type: str, operation: str, **kwargs):
        """Log an agent interaction for these research results."""
        return AgentInteraction.objects.create(
            agent_type=agent_type,
            operation=operation,
            entity_type="research_results",
            entity_id=self.id,
            **kwargs,
        )


class ResearchSources(models.Model):
    """Sources used in research analysis."""

    id = models.CharField(max_length=26, primary_key=True)
    security = models.ForeignKey(Universe, on_delete=models.CASCADE)
    url = models.URLField(max_length=2048)
    title = models.CharField(max_length=500, null=True, blank=True)
    snippet = models.TextField(blank=True)
    source_type = models.CharField(max_length=50)
    category = models.CharField(max_length=50)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "research_sources"
        verbose_name = "Research Source"
        verbose_name_plural = "Research Sources"
        indexes = [
            models.Index(
                fields=["security", "source_type"],
                name="sources_security_idx",
            ),
            models.Index(fields=["category"], name="sources_category_idx"),
        ]
        unique_together = [("security", "url")]

    def __str__(self) -> str:
        return f"{self.security.ticker} - {self.title or self.url}"


class Exclusion(models.Model):
    """Companies excluded from analysis for various reasons."""

    id = models.CharField(max_length=26, primary_key=True)
    security = models.ForeignKey(Universe, on_delete=models.CASCADE)
    category = models.CharField(max_length=50)
    criteria = models.CharField(max_length=100)
    concerned_groups = models.CharField(max_length=255, null=True, blank=True)
    decision = models.CharField(max_length=50)
    excluded_date = models.CharField(max_length=50, null=True, blank=True)
    notes = models.TextField(blank=True)
    is_historical = models.BooleanField(default=False)
    excluded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "exclusions"
        indexes = [
            models.Index(fields=["security"], name="exclusion_security_idx"),
            models.Index(
                fields=["category", "criteria"],
                name="exclusion_category_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.security.ticker} - {self.category}"


class TickHistory(models.Model):
    """Track historical tick changes for securities."""

    id = models.CharField(max_length=26, primary_key=True)
    security = models.ForeignKey(Universe, on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)
    old_tick = models.IntegerField(null=True)
    new_tick = models.IntegerField()
    note = models.TextField(blank=True)
    updated_by = models.CharField(max_length=255)

    class Meta:
        db_table = "tick_history"
        verbose_name = "Tick History"
        verbose_name_plural = "Tick History"
        indexes = [
            models.Index(fields=["security", "date"], name="tick_security_date_idx"),
        ]
        unique_together = [("security", "date")]

    def __str__(self) -> str:
        return f"{self.security.ticker} - {self.date} ({self.new_tick})"
