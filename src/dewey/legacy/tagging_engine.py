
# Refactored from: tagging_engine
# Date: 2025-03-16T16:19:10.195784
# Refactor Version: 1.0
import logging
from datetime import datetime
from enum import Enum

from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool

logger = logging.getLogger("uvicorn")


class TagCategory(Enum):
    DOCUMENT_TYPE = "document_type"
    FINANCIAL_METRIC = "financial_metric"
    RISK_LEVEL = "risk_level"
    ACTION_REQUIRED = "action_required"
    CLIENT_STATUS = "client_status"
    INVESTMENT_TYPE = "investment_type"
    TIME_HORIZON = "time_horizon"
    PRIORITY_LEVEL = "priority_level"
    FOLLOW_UP = "follow_up"


class TaggingTimeline:
    def __init__(self) -> None:
        self.operations = []

    def add_operation(self, operation: str, result: dict) -> None:
        self.operations.append(
            {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "result": result,
            },
        )

    def get_timeline(self) -> list:
        return self.operations

    def clear_timeline(self) -> None:
        self.operations = []


class LLMTagger:
    def __init__(self) -> None:
        self.agent = self._create_tagging_agent()
        self.timeline = TaggingTimeline()

    def _create_tagging_agent(self):
        tools = [
            FunctionTool.from_defaults(fn=self._tag_document_type),
            FunctionTool.from_defaults(fn=self._tag_financial_metrics),
            FunctionTool.from_defaults(fn=self._tag_risk_level),
            FunctionTool.from_defaults(fn=self._tag_actions),
        ]
        return ReActAgent.from_tools(tools)

    async def tag_document(self, text: str) -> dict:
        """Use LLM to analyze and tag document."""
        response = await self.agent.achat(
            f"Analyze this financial document and apply appropriate tags:\n{text}",
        )
        tags = self._parse_response(response)
        self.timeline.add_operation("llm_tagging", tags)
        return tags

    def _parse_response(self, response) -> dict:
        # Parse LLM response into structured tags
        # This will be implemented based on the LLM response format
        return {}


class TaggingEngine:
    def __init__(self) -> None:
        self.timeline = TaggingTimeline()
        self.llm_tagger = LLMTagger()

    def apply_tags(self, metadata: dict) -> dict:
        """Apply tags based on document metadata."""
        tags = {cat.value: [] for cat in TagCategory}

        # Atomic tagging operations
        doc_type_tags = self._tag_document_type(metadata)
        tags.update(doc_type_tags)
        self.timeline.add_operation("document_type_tagging", doc_type_tags)

        financial_tags = self._tag_financial_metrics(metadata)
        tags.update(financial_tags)
        self.timeline.add_operation("financial_metrics_tagging", financial_tags)

        risk_tags = self._tag_risk_level(metadata)
        tags.update(risk_tags)
        self.timeline.add_operation("risk_level_tagging", risk_tags)

        client_tags = self._tag_client_status(metadata)
        tags.update(client_tags)
        self.timeline.add_operation("client_status_tagging", client_tags)

        return tags

    @staticmethod
    def _tag_document_type(metadata) -> dict:
        """Atomic operation to tag document type."""
        tags = {}
        doc_type = metadata.get("document_type", "").lower()

        if "balance sheet" in doc_type:
            tags[TagCategory.DOCUMENT_TYPE.value] = ["balance_sheet"]
        elif "income statement" in doc_type:
            tags[TagCategory.DOCUMENT_TYPE.value] = ["income_statement"]
        elif "cash flow" in doc_type:
            tags[TagCategory.DOCUMENT_TYPE.value] = ["cash_flow_statement"]

        return tags

    @staticmethod
    def _tag_financial_metrics(metadata) -> dict:
        """Atomic operation to tag financial metrics."""
        tags = {}
        metrics = []

        if metadata.get("total_assets"):
            metrics.append("assets_reported")
        if metadata.get("total_liabilities"):
            metrics.append("liabilities_reported")
        if metadata.get("revenue"):
            metrics.append("revenue_reported")
        if metadata.get("net_income"):
            metrics.append("net_income_reported")

        if metrics:
            tags[TagCategory.FINANCIAL_METRIC.value] = metrics

        return tags

    @staticmethod
    def _tag_risk_level(metadata) -> dict:
        """Atomic operation to calculate and tag risk level."""
        tags = {}

        if metadata.get("net_worth") and metadata.get("total_liabilities"):
            debt_ratio = metadata["total_liabilities"] / metadata["net_worth"]
            if debt_ratio > 1:
                tags[TagCategory.RISK_LEVEL.value] = ["high_risk"]
            elif debt_ratio > 0.5:
                tags[TagCategory.RISK_LEVEL.value] = ["medium_risk"]
            else:
                tags[TagCategory.RISK_LEVEL.value] = ["low_risk"]

        return tags

    @staticmethod
    def _tag_client_status(metadata) -> dict:
        """Atomic operation to tag client status."""
        tags = {}
        status = metadata.get("client_status", "").lower()

        if "active" in status:
            tags[TagCategory.CLIENT_STATUS.value] = ["active"]
        elif "prospect" in status:
            tags[TagCategory.CLIENT_STATUS.value] = ["prospect"]
        elif "inactive" in status:
            tags[TagCategory.CLIENT_STATUS.value] = ["inactive"]

        return tags

    async def apply_llm_tags(self, text: str) -> dict:
        """Apply LLM-based tags to document text."""
        return await self.llm_tagger.tag_document(text)
