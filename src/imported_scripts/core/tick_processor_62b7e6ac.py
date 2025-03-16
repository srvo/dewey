"""Tick processor service for periodic updates."""

import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TickProcessor:
    """Process periodic updates."""

    def __init__(self, tick_interval: int = 60) -> None:
        """Initialize the tick processor.

        Args:
        ----
            tick_interval: The interval between ticks in seconds.

        """
        self.tick_interval: int = tick_interval
        self._task: asyncio.Task | None = None
        self._running: bool = False

    def start(self) -> None:
        """Start the tick processor."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run())
            logger.info("Tick processor started")

    def stop(self) -> None:
        """Stop the tick processor."""
        if self._running:
            self._running = False
            if self._task:
                self._task.cancel()
            logger.info("Tick processor stopped")

    async def _run(self) -> None:
        """Run the tick processor."""
        try:
            while self._running:
                await self._process_tick()
                await asyncio.sleep(self.tick_interval)
        except asyncio.CancelledError:
            logger.info("Tick processor cancelled")
        except Exception as e:
            logger.exception(f"Error in tick processor: {e}")
            self._running = False

    async def _process_tick(self) -> None:
        """Process a single tick."""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.debug(f"Processing tick at {current_time}")
            # Add any periodic processing here
        except Exception as e:
            logger.exception(f"Error processing tick: {e}")
