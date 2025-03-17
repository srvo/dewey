"""Base workflow module."""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from ethifinx.core.config import config
from ethifinx.core.logging_config import setup_logging

logger = setup_logging(__name__)


class ResearchWorkflow(ABC):
    """Base class for research workflows."""

    @abstractmethod
    def execute(self, data_dir: Optional[str] = None) -> Dict:
        """
        Execute the workflow.

        Args:
            data_dir: Optional directory for data files. If not provided,
                     uses the default from config.

        Returns:
            Dictionary containing workflow results and statistics.
        """
        pass
