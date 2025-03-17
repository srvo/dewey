# Refactored from: lunar_widget
# Date: 2025-03-16T16:19:10.322191
# Refactor Version: 1.0
"""Lunar phase widget for investment correlation."""

from datetime import datetime

import ephem

from .base import BaseWidget


class LunarWidget(BaseWidget):
    """Widget for displaying lunar phase and investment correlations."""

    def __init__(self) -> None:
        """Initialize the lunar widget."""
        super().__init__()
        self.observer = ephem.Observer()
        self.moon = ephem.Moon()

    def compose_content(self) -> None:
        """Compose the lunar widget content."""
        try:
            # Update current time and moon phase
            self.observer.date = datetime.utcnow()
            self.moon.compute(self.observer)

            # Calculate moon phase and illumination
            phase = self.moon.phase
            illumination = self.moon.phase / 100.0

            # Determine investment sentiment based on moon phase
            sentiment = self._calculate_sentiment(phase)

            # Format the display
            content = self._format_display(phase, illumination, sentiment)
            self.update(content)

        except Exception as e:
            self.handle_error(f"Error updating lunar data: {e!s}")

    def _calculate_sentiment(self, phase: float) -> tuple[str, str]:
        """Calculate investment sentiment based on moon phase."""
        if 0 <= phase < 45:  # New Moon to Waxing Crescent
            return "Cautious", "Consider researching new opportunities"
        if 45 <= phase < 90:  # First Quarter
            return "Growing", "Good time for initial investments"
        if 90 <= phase < 135:  # Waxing Gibbous
            return "Optimistic", "Consider increasing positions"
        if 135 <= phase < 180:  # Full Moon
            return "Peak", "Review and rebalance portfolio"
        if 180 <= phase < 225:  # Waning Gibbous
            return "Consolidating", "Focus on strong performers"
        if 225 <= phase < 270:  # Last Quarter
            return "Contracting", "Consider taking profits"
        if 270 <= phase < 315:  # Waning Crescent
            return "Conservative", "Maintain defensive positions"
        # Back to New Moon
        return "Reset", "Prepare for new cycle"

    def _format_display(
        self,
        phase: float,
        illumination: float,
        sentiment: tuple[str, str],
    ) -> str:
        """Format the lunar display content."""
        moon_phase = self._get_moon_ascii(phase)
        sentiment_type, advice = sentiment

        return f"""[bold blue]Lunar Investment Guide[/]

{moon_phase}

[bold]Moon Phase:[/] {phase:.1f}°
[bold]Illumination:[/] {illumination:.1%}
[bold]Market Sentiment:[/] {sentiment_type}

[italic]{advice}[/]
"""

    def _get_moon_ascii(self, phase: float) -> str:
        """Get ASCII art representation of moon phase."""
        if 0 <= phase < 45:
            return "🌑"  # New Moon
        if 45 <= phase < 90:
            return "🌒"  # Waxing Crescent
        if 90 <= phase < 135:
            return "🌓"  # First Quarter
        if 135 <= phase < 180:
            return "🌔"  # Waxing Gibbous
        if 180 <= phase < 225:
            return "🌕"  # Full Moon
        if 225 <= phase < 270:
            return "🌖"  # Waning Gibbous
        if 270 <= phase < 315:
            return "🌗"  # Last Quarter
        return "🌘"  # Waning Crescent
