"""Unit tests for the ethical_analysis module."""

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dewey.core.research.analysis.ethical_analysis import (
    EthicalAnalysisWorkflow,
)
from dewey.core.engines.deepseek import ResearchResult, SearchResult


@pytest.fixture
def mock_deepseek_engine() -> MagicMock:
    """Fixture to mock the DeepSeekEngine."""
    return MagicMock()


@pytest.fixture
def ethical_analysis_workflow(mock_deepseek_engine: MagicMock) -> EthicalAnalysisWorkflow:
    """Fixture to create an EthicalAnalysisWorkflow instance with a mocked engine."""
    with patch(
        "dewey.core.research.analysis.ethical_analysis.DeepSeekEngine",
        return_value=mock_deepseek_engine,
    ):
        workflow = EthicalAnalysisWorkflow()
    return workflow


@pytest.fixture
def search_results_fixture() -> List[SearchResult]:
    """Fixture to provide a list of mock SearchResults."""
    return [
        SearchResult(
            title="Test Result 1",
            link="http://example.com/1",
            snippet="This is a test snippet 1.",
        ),
        SearchResult(
            title="Test Result 2",
            link="http://example.com/2",
            snippet="This is a test snippet 2.",
        ),
    ]


@pytest.fixture
def research_results_fixture() -> List[ResearchResult]:
    """Fixture to provide a list of mock ResearchResults."""
    return [
        ResearchResult(query="Test Query 1", result="Test Result 1"),
        ResearchResult(query="Test Query 2", result="Test Result 2"),
    ]


class TestEthicalAnalysisWorkflow:
    """Tests for the EthicalAnalysisWorkflow class."""

    def test_init(self, mock_deepseek_engine: MagicMock) -> None:
        """Test the __init__ method."""
        with patch(
            "dewey.core.research.analysis.ethical_analysis.DeepSeekEngine",
            return_value=mock_deepseek_engine,
        ):
            workflow = EthicalAnalysisWorkflow()
            assert workflow.engine == mock_deepseek_engine
            mock_deepseek_engine.add_template.assert_called()

    def test_init_templates(self, ethical_analysis_workflow: EthicalAnalysisWorkflow) -> None:
        """Test the _init_templates method."""
        # The _init_templates method is called during __init__, so we can just check
        # that the templates were added to the engine.
        assert ethical_analysis_workflow.engine.add_template.call_count == 2
        ethical_analysis_workflow.engine.add_template.assert_any_call(
            "ethical_analysis",
            [
                {
                    "role": "system",
                    "content": "You are an expert in ethical financial analysis. Focus on identifying potential ethical concerns, ESG issues, and risk factors.",
                },
                {
                    "role": "user",
                    "content": "Analyze the ethical profile of this company",
                },
                {
                    "role": "assistant",
                    "content": """I'll analyze the company's ethical profile focusing on:
1. Environmental Impact
2. Social Responsibility
3. Governance Structure
4. Ethical Controversies
4. Risk Assessment
5. Recommendations""",
                },
            ],
        )
        ethical_analysis_workflow.engine.add_template.assert_any_call(
            "risk_analysis",
            [
                {
                    "role": "system",
                    "content": "You are a risk assessment specialist focusing on ethical and reputational risks in finance.",
                },
                {
                    "role": "user",
                    "content": "What are the key risk factors for this company?",
                },
                {
                    "role": "assistant",
                    "content": """I'll assess the following risk categories:
1. Regulatory Compliance Risks
2. Environmental Risks
3. Social Impact Risks
4. Governance Risks
5. Reputational Risks
6. Mitigation Strategies""",
                },
            ],
        )

    @pytest.mark.asyncio
    async def test_analyze_company_profile(
        self,
        ethical_analysis_workflow: EthicalAnalysisWorkflow,
        search_results_fixture: List[SearchResult],
    ) -> None:
        """Test the analyze_company_profile method."""
        mock_analysis_result = {"key": "value"}
        ethical_analysis_workflow.engine.analyze = AsyncMock(return_value=mock_analysis_result)

        result = await ethical_analysis_workflow.analyze_company_profile(search_results_fixture)

        assert result == mock_analysis_result
        ethical_analysis_workflow.engine.analyze.assert_called_once_with(
            results=search_results_fixture, template_name="ethical_analysis"
        )

    @pytest.mark.asyncio
    async def test_assess_risks(
        self,
        ethical_analysis_workflow: EthicalAnalysisWorkflow,
        search_results_fixture: List[SearchResult],
    ) -> None:
        """Test the assess_risks method."""
        mock_risk_assessment_result = {"risk": "high"}
        ethical_analysis_workflow.engine.analyze = AsyncMock(
            return_value=mock_risk_assessment_result
        )

        result = await ethical_analysis_workflow.assess_risks(search_results_fixture)

        assert result == mock_risk_assessment_result
        ethical_analysis_workflow.engine.analyze.assert_called_once_with(
            results=search_results_fixture, template_name="risk_analysis"
        )

    @pytest.mark.asyncio
    async def test_conduct_deep_research(
        self,
        ethical_analysis_workflow: EthicalAnalysisWorkflow,
        research_results_fixture: List[ResearchResult],
    ) -> None:
        """Test the conduct_deep_research method."""
        initial_query = "What is the company's environmental impact?"
        follow_up_questions = ["What are their carbon emissions?", "What is their waste management policy?"]
        context = {"company_name": "Test Company"}
        ethical_analysis_workflow.engine.conduct_research = AsyncMock(
            return_value=research_results_fixture
        )

        result = await ethical_analysis_workflow.conduct_deep_research(
            initial_query, follow_up_questions, context
        )

        assert result == research_results_fixture
        ethical_analysis_workflow.engine.conduct_research.assert_called_once_with(
            initial_query=initial_query,
            follow_up_questions=follow_up_questions,
            context=context,
            template_name="ethical_analysis",
        )

    def test_run(self, ethical_analysis_workflow: EthicalAnalysisWorkflow) -> None:
        """Test the run method."""
        # The run method currently only logs messages, so we can just check that it runs without errors.
        ethical_analysis_workflow.run()
        # Add assertions here if the run method is updated to do more than just log messages.
