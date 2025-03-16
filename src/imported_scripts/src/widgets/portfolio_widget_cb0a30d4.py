"""Portfolio management widget."""

from decimal import Decimal

from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable

from .base import BaseWidget


class PortfolioWidget(BaseWidget):
    """Widget for managing investment portfolio."""

    BINDINGS = [
        Binding("a", "add_position", "Add"),
        Binding("e", "edit_position", "Edit"),
        Binding("d", "delete_position", "Delete"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self) -> None:
        """Initialize the portfolio widget."""
        super().__init__()
        self.positions: dict[str, dict] = {}
        self.selected_ticker: str | None = None

        # Initialize the data table
        self.table = DataTable()
        self.table.cursor_type = "row"

        # Set up columns
        self.table.add_columns(
            "Ticker",
            "Company",
            "Shares",
            "Cost Basis",
            "Current Price",
            "Market Value",
            "Gain/Loss",
            "ESG Score",
        )

    def compose(self) -> None:
        """Compose the portfolio widget."""
        with Vertical():
            with Horizontal():
                yield Button("Add Position", id="add-btn", variant="primary")
                yield Button("Edit Position", id="edit-btn", variant="primary")
                yield Button("Delete Position", id="delete-btn", variant="primary")
                yield Button("Refresh", id="refresh-btn", variant="primary")
            yield self.table

    async def update_content(self) -> None:
        """Update positions data."""
        # For now, just add some sample data
        if not self.positions:
            self.positions = {
                "AAPL": {
                    "company": "Apple Inc.",
                    "shares": 100,
                    "cost_basis": Decimal("150.00"),
                    "current_price": Decimal("175.00"),
                    "esg_score": 82,
                },
                "MSFT": {
                    "company": "Microsoft Corp.",
                    "shares": 50,
                    "cost_basis": Decimal("250.00"),
                    "current_price": Decimal("270.00"),
                    "esg_score": 78,
                },
            }

        # Update the table with current positions
        self.table.clear()
        for ticker, data in self.positions.items():
            market_value = data["shares"] * data["current_price"]
            gain_loss = market_value - (data["shares"] * data["cost_basis"])

            self.table.add_row(
                ticker,
                data["company"],
                str(data["shares"]),
                f"${data['cost_basis']:.2f}",
                f"${data['current_price']:.2f}",
                f"${market_value:.2f}",
                f"${gain_loss:.2f}",
                str(data["esg_score"]),
            )

    async def on_button_pressed(self, event) -> None:
        """Handle button presses."""
        button_id = event.button.id
        if button_id == "refresh-btn":
            await self.update_content()
        elif button_id == "add-btn":
            await self.add_position()
        elif button_id == "edit-btn":
            await self.edit_position()
        elif button_id == "delete-btn":
            await self.delete_position()

    async def add_position(self) -> None:
        """Add a new position."""
        # TODO: Implement add position dialog

    async def edit_position(self) -> None:
        """Edit the selected position."""
        # TODO: Implement edit position dialog

    async def delete_position(self) -> None:
        """Delete the selected position."""
        # TODO: Implement delete position confirmation
