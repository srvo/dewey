import pandas as pd
import plotext as plt
from celadon import View
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table


class CompanyDetailView(View):
    def __init__(self, universe_df, tick_history_df, ticker) -> None:
        super().__init__()
        self.universe_df = universe_df
        self.tick_history_df = tick_history_df
        self.ticker = ticker
        self.company_data = self.universe_df[self.universe_df["Ticker"] == ticker].iloc[
            0
        ]

    def get_tick_history(self):
        """Get historical tick data for plotting."""
        history = self.tick_history_df[self.tick_history_df["Ticker"] == self.ticker]
        return history.sort_values("Date")

    def render(self):
        layout = Layout()

        # Company header
        header = Panel(
            f"{self.company_data['Security Name']} ({self.ticker})\n"
            f"Current Tick: {self.company_data['Tick']}\n"
            f"Category: {self.company_data['Category']}\n"
            f"Sector: {self.company_data['Sector']}",
            title="Company Overview",
            style="cyan",
        )

        # Notes panel
        notes = Panel(
            (
                self.company_data["Note"]
                if pd.notna(self.company_data["Note"])
                else "No notes available"
            ),
            title="Research Notes",
            style="yellow",
        )

        # Tick history visualization
        history = self.get_tick_history()
        if not history.empty:
            plt.clear_data()
            plt.plot(history["Date"], history["New Tick"], marker="dot")
            plt.title("Tick History")
            tick_plot = plt.build()
        else:
            tick_plot = "No historical data available"

        # Combine views
        layout.split_column(
            Layout(header, name="header", size=4),
            Layout(notes, name="notes", size=4),
            Layout(Panel(tick_plot, title="Historical Ticks"), name="history"),
        )

        return layout


class CompanyListView(View):
    def __init__(self, universe_df, sort_by="Tick", ascending=False) -> None:
        super().__init__()
        self.universe_df = universe_df
        self.sort_by = sort_by
        self.ascending = ascending

    def render(self):
        # Sort companies by specified column
        sorted_df = self.universe_df.sort_values(self.sort_by, ascending=self.ascending)

        table = Table(title="Company Universe")
        table.add_column("Ticker")
        table.add_column("Name")
        table.add_column("Tick")
        table.add_column("Category")

        for _, row in sorted_df.head(20).iterrows():
            table.add_row(
                row["Ticker"],
                row["Security Name"],
                str(row["Tick"]),
                row["Category"] if pd.notna(row["Category"]) else "",
            )

        return Panel(table, title="Top Companies by Tick")
