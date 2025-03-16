import ephem
from datetime import datetime, timedelta
import pandas as pd
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Header, Footer, Static, Label
from textual.binding import Binding
from textual.reactive import reactive
import sys
import tracebacksudo apt update
sudo apt install docker.io docker-compose -y
sudo systemctl enable docker
sudo systemctl start docker
import asyncio
from rss_reader import RSSManager
from sec_filings import SECFilingsManager
import os

MOON_PHASES = {
    0: " New Moon",      # 0
    1: " Waxing Crescent", # 0-0.25
    2: " First Quarter",   # 0.25
    3: " Waxing Gibbous",  # 0.25-0.5
    4: " Full Moon",       # 0.5
    5: " Waning Gibbous",  # 0.5-0.75
    6: " Last Quarter",    # 0.75
    7: " Waning Crescent", # 0.75-1
}

class BaseWidget(Static):
    """Base widget with error handling."""
    def on_mount(self) -> None:
        try:
            self.compose_content()
        except Exception as e:
            self.update(f"Error: {str(e)}")

    def compose_content(self) -> None:
        """Override this method in child classes."""
        pass

class LunarCalendarWidget(BaseWidget):
    """A widget showing detailed moon phase information."""
    
    def get_moon_phase(self, date=None):
        """Get current moon phase and phase number (0-7)."""
        if date is None:
            date = datetime.now()
            
        moon = ephem.Moon()
        moon.compute(date)
        
        # Get illuminated percentage
        phase = moon.phase / 100.0
        
        # Determine phase number
        if phase <= 0.01:  # New moon
            return 0
        elif phase < 0.25:  # Waxing crescent
            return 1
        elif abs(phase - 0.25) <= 0.01:  # First quarter
            return 2
        elif phase < 0.5:  # Waxing gibbous
            return 3
        elif abs(phase - 0.5) <= 0.01:  # Full moon
            return 4
        elif phase < 0.75:  # Waning gibbous
            return 5
        elif abs(phase - 0.75) <= 0.01:  # Last quarter
            return 6
        else:  # Waning crescent
            return 7
    
    def compose_content(self) -> None:
        try:
            # Calculate next new moon
            next_new_moon = ephem.next_new_moon(datetime.now())
            next_new_moon_date = ephem.Date(next_new_moon).datetime()
            days_until = (next_new_moon_date - datetime.now()).days
            
            # Get current moon phase
            current_phase = self.get_moon_phase()
            
            # Create the phase display
            phase_display = []
            for phase_num in range(8):
                if phase_num == current_phase:
                    phase_display.append(f"[bold white on blue]{MOON_PHASES[phase_num]}[/]")
                else:
                    phase_display.append(f"{MOON_PHASES[phase_num]}")
            
            # Create the content
            content = "\n".join([
                "[bold]Lunar Calendar[/]",
                "",
                "Current Phase:",
                phase_display[current_phase],
                "",
                "All Phases:",
                " → ".join(phase_display[:4]),
                " → ".join(phase_display[4:]),
                "",
                f"Next New Moon: [bold]{next_new_moon_date.strftime('%Y-%m-%d')}[/]",
                f"Days until rebalance: [bold]{days_until}[/]"
            ])
            
            self.update(content)
            
        except Exception as e:
            self.update(f"Error calculating lunar data: {str(e)}")

class PortfolioHealthWidget(BaseWidget):
    """A widget showing portfolio health metrics."""
    
    def __init__(self, universe_df):
        super().__init__()
        self.universe_df = universe_df
    
    def compose_content(self) -> None:
        try:
            active_holdings = len(self.universe_df[self.universe_df['Tick'] > 10])
            avg_tick = self.universe_df['Tick'].mean()
            
            self.update(
                f"Active Holdings: {active_holdings}\n"
                f"Average Tick: {avg_tick:.1f}"
            )
        except Exception as e:
            self.update(f"Error calculating portfolio health: {str(e)}")

class ReviewQueueWidget(BaseWidget):
    """A widget showing companies due for review."""
    
    def __init__(self, universe_df):
        super().__init__()
        self.universe_df = universe_df
    
    def compose_content(self) -> None:
        try:
            # Get companies due for lunar review (tick > 10)
            lunar_queue = self.universe_df[self.universe_df['Tick'] > 10]['Security Name'].tolist()[:5]
            
            # Get companies with ticks between -1 and 1
            transition_queue = self.universe_df[
                (self.universe_df['Tick'] >= -1) & 
                (self.universe_df['Tick'] <= 1)
            ]['Security Name'].tolist()[:5]
            
            content = "Due for Lunar Review:\n"
            content += "\n".join(f"• {company}" for company in lunar_queue)
            content += "\n\nPotential Transitions (-1 to 1):\n"
            content += "\n".join(f"• {company}" for company in transition_queue)
            
            self.update(content)
        except Exception as e:
            self.update(f"Error generating review queue: {str(e)}")

class CompanyListWidget(BaseWidget):
    """A widget showing the list of companies."""
    
    def __init__(self, universe_df):
        super().__init__()
        self.universe_df = universe_df
    
    def compose_content(self) -> None:
        try:
            content = []
            for _, row in self.universe_df.iterrows():
                content.append(
                    f"{row['Ticker']} | {row['Security Name']} | "
                    f"Tick: {row['Tick']} | {row['Category']}"
                )
            self.update("\n".join(content))
        except Exception as e:
            self.update(f"Error displaying company list: {str(e)}")

class RSSWidget(BaseWidget):
    """A widget showing RSS feeds."""
    
    def __init__(self, rss_manager: RSSManager):
        super().__init__()
        self.rss_manager = rss_manager
        self.current_feed = None
    
    def compose_content(self) -> None:
        try:
            entries = self.rss_manager.get_latest_entries(self.current_feed, limit=5)
            
            content = ["[bold]Latest News[/]", ""]
            
            for entry in entries:
                pub_date = ""
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6]).strftime('%Y-%m-%d %H:%M')
                
                feed_title = entry.get('feed_title', '')
                title = entry.get('title', 'No title')
                
                content.append(f"[bold blue]{feed_title}[/] - {pub_date}")
                content.append(f"[bold]{title}[/]")
                content.append("")
            
            self.update("\n".join(content))
            
        except Exception as e:
            self.update(f"Error displaying RSS feeds: {str(e)}")

class FilingsWidget(BaseWidget):
    """A widget showing SEC filings for companies."""
    
    def __init__(self, sec_manager: SECFilingsManager, universe_df: pd.DataFrame):
        super().__init__()
        self.sec_manager = sec_manager
        self.universe_df = universe_df
        self.current_ticker = None
        
    def compose_content(self) -> None:
        try:
            if not self.current_ticker:
                self.update("[bold]Select a company to view SEC filings[/]")
                return
                
            # Get filings for the company
            filings_df = self.sec_manager.get_cached_filings(self.current_ticker)
            
            if filings_df.empty:
                self.update(f"[bold]No filings found for {self.current_ticker}[/]\nFetching latest filings...")
                return
            
            content = [f"[bold]SEC Filings for {self.current_ticker}[/]", ""]
            
            # Group by filing type
            for filing_type in filings_df['type'].unique():
                type_filings = filings_df[filings_df['type'] == filing_type]
                content.append(f"[bold blue]{filing_type}[/]")
                
                for _, filing in type_filings.iterrows():
                    date_str = pd.to_datetime(filing['date']).strftime('%Y-%m-%d')
                    content.append(f"{date_str} - [link={filing['url']}]View Filing[/link]")
                content.append("")
            
            self.update("\n".join(content))
            
        except Exception as e:
            self.update(f"Error displaying filings: {str(e)}")

class EthicalPortfolioApp(App):
    """The main Ethical Portfolio application."""
    
    TITLE = "Ethical Capital Investment Collaborative"
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2;
        grid-gutter: 1;
        padding: 1;
    }
    
    .widget {
        height: 100%;
        border: solid $primary-lighten-2;
        padding: 1;
        background: $surface;
    }

    .lunar {
        border: double $primary;
        background: $surface-darken-1;
    }

    .news {
        height: 100%;
        border: solid $warning;
        background: $surface;
        padding: 1;
        overflow: auto;
    }

    Footer {
        height: 3;
        background: $primary-background;
        color: $text;
        dock: bottom;
        content-align: center middle;
        padding: 0 1;
    }

    Footer > .footer--key {
        background: $primary-lighten-2;
        color: $text;
        min-width: 4;
        padding: 0 1;
        text-align: center;
    }

    Footer > .footer--description {
        color: $text;
        padding: 0 2;
        text-style: bold;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("l", "show_list", "Company List"),
        Binding("h", "show_help", "Help"),
        Binding("r", "show_review", "Review Queue"),
        Binding("n", "show_news", "News Feed"),
        Binding("v", "view_data", "View Data"),
        Binding("f", "show_filings", "SEC Filings"),
        Binding("esc", "show_main", "Main View"),
    ]
    
    current_view = reactive("main")
    selected_ticker = reactive(None)
    
    def __init__(self):
        super().__init__()
        try:
            # Load data
            self.universe_df = pd.read_csv('universe.csv')
            
            # Initialize managers
            self.rss_manager = RSSManager(self.universe_df)
            self.sec_manager = SECFilingsManager()
            
            # Initialize widgets
            self.lunar_widget = LunarCalendarWidget()
            self.health_widget = PortfolioHealthWidget(self.universe_df)
            self.review_widget = ReviewQueueWidget(self.universe_df)
            self.company_list = CompanyListWidget(self.universe_df)
            self.news_widget = RSSWidget(self.rss_manager)
            self.filings_widget = FilingsWidget(self.sec_manager, self.universe_df)
            
        except Exception as e:
            print(f"Error initializing application: {str(e)}")
            traceback.print_exc()
            sys.exit(1)
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        
        try:
            if self.current_view == "main":
                yield Container(
                    Horizontal(
                        Container(self.lunar_widget, classes="widget lunar"),
                        Container(self.health_widget, classes="widget")
                    ),
                    Container(
                        Horizontal(
                            Container(self.review_widget, classes="widget"),
                            Container(self.news_widget, classes="widget news")
                        )
                    )
                )
            elif self.current_view == "list":
                yield Container(self.company_list, classes="widget")
            elif self.current_view == "news":
                yield ScrollableContainer(self.news_widget, classes="widget news")
            elif self.current_view == "filings":
                yield ScrollableContainer(self.filings_widget, classes="widget")
            
            yield Footer()
            
        except Exception as e:
            yield Label(f"Error composing view: {str(e)}")
            yield Footer()
    
    def watch_selected_ticker(self, ticker: str) -> None:
        """React to ticker selection changes."""
        if self.filings_widget:
            self.filings_widget.current_ticker = ticker
            self.refresh()
    
    async def on_mount(self) -> None:
        """Initialize data when the app starts."""
        await self.rss_manager.fetch_all()
        
        # Fetch initial SEC filings for all companies
        for ticker in self.universe_df['Ticker'].unique():
            await self.sec_manager.get_company_filings(ticker)
    
    def action_show_list(self) -> None:
        """Switch to the company list view."""
        self.current_view = "list"
        self.refresh()
    
    def action_show_main(self) -> None:
        """Switch to the main view."""
        self.current_view = "main"
        self.refresh()
    
    def action_show_review(self) -> None:
        """Switch to the main view (review queue is there)."""
        self.current_view = "main"
        self.refresh()
    
    def action_show_news(self) -> None:
        """Switch to the news view."""
        self.current_view = "news"
        self.refresh()
    
    def action_show_help(self) -> None:
        """Show the help screen."""
        self.current_view = "help"
        self.refresh()
    
    async def action_view_data(self) -> None:
        """Open the current view's data in VisiData."""
        try:
            # Save current data to a temporary CSV file
            if self.current_view == "list":
                temp_file = "company_list_temp.csv"
                self.universe_df.to_csv(temp_file, index=False)
            elif self.current_view == "review":
                temp_file = "review_queue_temp.csv"
                # Get companies due for review
                today = pd.Timestamp.now()
                review_df = self.universe_df[
                    (self.universe_df['Last Review'].isna()) |
                    (pd.to_datetime(self.universe_df['Last Review']) < today - pd.Timedelta(days=28))
                ]
                review_df.to_csv(temp_file, index=False)
            else:
                temp_file = "universe_temp.csv"
                self.universe_df.to_csv(temp_file, index=False)
            
            # Launch VisiData in a new terminal window
            await self.run_command_in_terminal(["vd", temp_file])
            
        except Exception as e:
            self.notify(f"Error viewing data: {str(e)}", severity="error")
    
    def action_show_filings(self) -> None:
        """Switch to the SEC filings view."""
        self.current_view = "filings"
        self.refresh()
        
    async def run_command_in_terminal(self, command: list) -> None:
        """Run a command in a new terminal window."""
        try:
            # For macOS, use Terminal.app
            osascript_command = [
                'osascript',
                '-e',
                f'tell application "Terminal" to do script "{" ".join(command)}"'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *osascript_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
        except Exception as e:
            self.notify(f"Error running terminal command: {str(e)}", severity="error")

def main():
    try:
        app = EthicalPortfolioApp()
        app.run()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
