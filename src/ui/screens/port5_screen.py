"""Port5 Screen

A Textual screen for integrating the ethifinx research modules into the Dewey TUI system.
"""

import os

# Import ethifinx components
import sys
from typing import Any, Dict, List, Optional

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    LoadingIndicator,
    Static,
    TextArea,
)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.dewey.core.research.engines.deepseek import DeepSeekEngine
from src.dewey.core.research.search_flow import (
    get_research_status,
    get_top_companies,
)
from src.dewey.core.research.workflows.analysis_tagger import AnalysisTaggingWorkflow


class CompanyAnalysisResult:
    """Represents an analysis result for a company."""

    def __init__(
        self,
        ticker: str,
        name: str,
        risk_score: int | None = None,
        confidence_score: float | None = None,
        recommendation: str | None = None,
        primary_themes: list[str] | None = None,
        summary: str | None = None,
        error: str | None = None,
    ):
        self.ticker = ticker
        self.name = name
        self.risk_score = risk_score
        self.confidence_score = confidence_score
        self.recommendation = recommendation
        self.primary_themes = primary_themes or []
        self.summary = summary
        self.error = error
        self.timestamp = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CompanyAnalysisResult":
        """Create a CompanyAnalysisResult from a dictionary."""
        ticker = data.get("ticker", "")
        name = data.get("name", "")
        error = data.get("error")

        if error:
            return cls(ticker=ticker, name=name, error=error)

        tags = data.get("tags", {})
        summary_data = data.get("summary", {})

        return cls(
            ticker=ticker,
            name=name,
            risk_score=tags.get("concern_level"),
            confidence_score=tags.get("confidence_score"),
            recommendation=summary_data.get("recommendation"),
            primary_themes=tags.get("primary_themes", [])[:3],
            summary=summary_data.get("summary"),
        )


class Port5Screen(Screen):
    """Port5 (ethifinx) research screen for the Dewey TUI system."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("a", "analyze", "Analyze"),
        Binding("t", "top_companies", "Top Companies"),
        Binding("s", "status", "Status"),
    ]

    # Reactive state
    selected_company_index = reactive(-1)
    is_analyzing = reactive(False)
    status_data = reactive({})

    def __init__(self):
        super().__init__()
        self.companies = []
        self.analysis_results = []

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        yield Header("Port5 Research Platform")

        with Container(id="main-container"):
            with Horizontal(id="search-container"):
                yield Input(
                    placeholder="Enter ticker(s) separated by commas", id="ticker-input"
                )
                yield Button("Analyze", variant="primary", id="analyze-button")
                yield Button("Top Companies", id="top-companies-button")
                yield Button("Status", id="status-button")

            with Horizontal(id="content-container"):
                with Vertical(id="companies-container"):
                    yield Static(
                        "Companies", id="companies-header", classes="section-header"
                    )
                    yield DataTable(id="companies-table")

                with Vertical(id="details-container"):
                    yield Static(
                        "Analysis Results",
                        id="details-header",
                        classes="section-header",
                    )
                    with Vertical(id="analysis-details"):
                        yield Static("", id="company-name")
                        yield Static("", id="risk-score")
                        yield Static("", id="confidence-score")
                        yield Static("", id="recommendation")
                        yield Static("", id="themes")
                        yield TextArea("", id="summary-text", read_only=True)

            with Horizontal(id="status-container"):
                yield LoadingIndicator(id="loading-indicator")
                yield Static("Ready", id="status-text")

        yield Footer()

    def on_mount(self) -> None:
        """Handle screen mount event."""
        self.setup_tables()
        self.query_one("#loading-indicator", LoadingIndicator).display = False

    def setup_tables(self) -> None:
        """Set up the data tables."""
        companies_table = self.query_one("#companies-table", DataTable)
        companies_table.add_columns("Ticker", "Name", "Risk", "Recommendation")
        companies_table.cursor_type = "row"

    @on(Button.Pressed, "#analyze-button")
    def handle_analyze_button(self) -> None:
        """Handle analyze button press."""
        self.action_analyze()

    @on(Button.Pressed, "#top-companies-button")
    def handle_top_companies_button(self) -> None:
        """Handle top companies button press."""
        self.action_top_companies()

    @on(Button.Pressed, "#status-button")
    def handle_status_button(self) -> None:
        """Handle status button press."""
        self.action_status()

    @on(DataTable.CellSelected)
    def handle_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Handle cell selection in the companies table."""
        table_id = event.data_table.id
        if table_id == "companies-table":
            self.selected_company_index = event.coordinate.row
            self.update_analysis_details()

    def update_analysis_details(self) -> None:
        """Update the analysis details view."""
        if self.selected_company_index < 0 or self.selected_company_index >= len(
            self.analysis_results
        ):
            self.clear_analysis_details()
            return

        result = self.analysis_results[self.selected_company_index]

        if result.error:
            self.query_one("#company-name", Static).update(
                f"Company: {result.name} ({result.ticker})"
            )
            self.query_one("#risk-score", Static).update("Error analyzing company")
            self.query_one("#confidence-score", Static).update("")
            self.query_one("#recommendation", Static).update("")
            self.query_one("#themes", Static).update("")
            self.query_one("#summary-text", TextArea).value = f"Error: {result.error}"
            return

        self.query_one("#company-name", Static).update(
            f"Company: {result.name} ({result.ticker})"
        )
        self.query_one("#risk-score", Static).update(
            f"Risk Score: {result.risk_score}/5"
        )
        self.query_one("#confidence-score", Static).update(
            f"Confidence: {result.confidence_score:.2f if result.confidence_score else 'N/A'}"
        )
        self.query_one("#recommendation", Static).update(
            f"Recommendation: {result.recommendation or 'N/A'}"
        )

        themes_text = (
            "Primary Themes: " + ", ".join(result.primary_themes)
            if result.primary_themes
            else "No themes identified"
        )
        self.query_one("#themes", Static).update(themes_text)

        self.query_one("#summary-text", TextArea).value = (
            result.summary or "No summary available"
        )

    def clear_analysis_details(self) -> None:
        """Clear the analysis details view."""
        self.query_one("#company-name", Static).update("")
        self.query_one("#risk-score", Static).update("")
        self.query_one("#confidence-score", Static).update("")
        self.query_one("#recommendation", Static).update("")
        self.query_one("#themes", Static).update("")
        self.query_one("#summary-text", TextArea).value = ""

    @work
    async def analyze_tickers(self, tickers: list[str]) -> None:
        """Analyze a list of ticker symbols."""
        self.is_analyzing = True
        self.query_one("#status-text", Static).update(
            f"Analyzing {len(tickers)} companies..."
        )
        self.query_one("#loading-indicator", LoadingIndicator).display = True

        # Clear existing results
        self.companies = []
        self.analysis_results = []

        companies_table = self.query_one("#companies-table", DataTable)
        companies_table.clear()

        # Initialize the analysis workflow
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        engine = DeepSeekEngine(api_key)
        workflow = AnalysisTaggingWorkflow(engine)

        async for result in workflow.process_companies_by_tickers(tickers):
            # Convert the result to a CompanyAnalysisResult object
            analysis_result = CompanyAnalysisResult.from_dict(result)
            self.analysis_results.append(analysis_result)

            # Add the company to the table
            risk_display = (
                f"{analysis_result.risk_score}/5"
                if analysis_result.risk_score
                else "Error"
            )
            recommendation = analysis_result.recommendation or "N/A"
            companies_table.add_row(
                analysis_result.ticker,
                analysis_result.name,
                risk_display,
                recommendation,
            )

            # Update status
            self.query_one("#status-text", Static).update(
                f"Analyzed {len(self.analysis_results)}/{len(tickers)} companies"
            )

        # Reset UI state
        self.is_analyzing = False
        self.query_one("#loading-indicator", LoadingIndicator).display = False
        self.query_one("#status-text", Static).update(
            f"Analysis complete: {len(self.analysis_results)} companies"
        )

        # Select the first result if available
        if companies_table.row_count > 0:
            companies_table.cursor_coordinates = (0, 0)
            self.selected_company_index = 0
            self.update_analysis_details()

    @work
    async def load_top_companies(self, limit: int = 20) -> None:
        """Load top companies for analysis."""
        self.query_one("#status-text", Static).update(
            f"Loading top {limit} companies..."
        )
        self.query_one("#loading-indicator", LoadingIndicator).display = True

        # Get top companies
        companies = get_top_companies(limit=limit)

        # Update UI with company data
        self.query_one("#status-text", Static).update(
            f"Loaded {len(companies)} companies"
        )
        self.query_one("#loading-indicator", LoadingIndicator).display = False

        # Clear existing data
        self.companies = companies
        self.analysis_results = []

        # Populate table
        companies_table = self.query_one("#companies-table", DataTable)
        companies_table.clear()

        for company in companies:
            companies_table.add_row(
                company.get("ticker", ""), company.get("name", ""), "N/A", "N/A"
            )

        # Update status
        self.query_one("#status-text", Static).update(
            f"Ready to analyze {len(companies)} companies"
        )

    @work
    async def load_research_status(self) -> None:
        """Load research status information."""
        self.query_one("#status-text", Static).update("Loading research status...")
        self.query_one("#loading-indicator", LoadingIndicator).display = True

        # Get research status
        status = get_research_status()
        self.status_data = status

        # Display status information in the summary area
        summary = (
            f"Research Status\n\n"
            f"Total companies: {status['total']}\n"
            f"Completed: {status['completed']}\n"
            f"In progress: {status['in_progress']}\n"
            f"Failed: {status['failed']}\n"
            f"Not started: {status['not_started']}\n"
            f"Completion: {status['completion_percentage']:.2f}%"
        )

        self.query_one("#summary-text", TextArea).value = summary

        # Update company name as a header
        self.query_one("#company-name", Static).update("Research Platform Status")

        # Clear other fields
        self.query_one("#risk-score", Static).update("")
        self.query_one("#confidence-score", Static).update("")
        self.query_one("#recommendation", Static).update("")
        self.query_one("#themes", Static).update("")

        # Update status
        self.query_one("#status-text", Static).update("Research status loaded")
        self.query_one("#loading-indicator", LoadingIndicator).display = False

    def action_analyze(self) -> None:
        """Analyze ticker(s) entered in the input field."""
        ticker_input = self.query_one("#ticker-input", Input)
        ticker_text = ticker_input.value.strip()

        if not ticker_text:
            # If no tickers provided but companies are loaded, use those tickers
            if self.companies:
                tickers = [
                    company.get("ticker")
                    for company in self.companies
                    if company.get("ticker")
                ]
                self.analyze_tickers(tickers)
            else:
                self.notify("Please enter ticker symbols to analyze", severity="error")
        else:
            # Parse tickers from input
            tickers = [t.strip().upper() for t in ticker_text.split(",") if t.strip()]
            if not tickers:
                self.notify("Please enter valid ticker symbols", severity="error")
                return

            self.analyze_tickers(tickers)

    def action_top_companies(self) -> None:
        """Load top companies for analysis."""
        self.load_top_companies()

    def action_status(self) -> None:
        """Load and display research status."""
        self.load_research_status()

    def action_refresh(self) -> None:
        """Refresh the current view."""
        if self.is_analyzing:
            self.notify("Analysis in progress, please wait", severity="warning")
            return

        if self.companies:
            self.load_top_companies(len(self.companies))
        else:
            self.load_top_companies()
