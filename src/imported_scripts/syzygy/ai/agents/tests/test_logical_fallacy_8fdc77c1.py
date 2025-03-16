"""Tests for the logical fallacy detection agent."""

import pytest
from syzygy.ai.agents.logical_fallacy import (
    FallacyAnalysis,
    FallacyInstance,
    LogicalFallacyAgent,
)


@pytest.fixture
def fallacy_agent():
    """Create a logical fallacy agent for testing."""
    return LogicalFallacyAgent()


@pytest.mark.asyncio
async def test_analyze_text_with_ad_hominem(fallacy_agent) -> None:
    """Test detection of ad hominem fallacy."""
    text = """
    You can't trust Dr. Smith's research on climate change because he drives a gas-guzzling SUV.
    This clearly shows he doesn't really care about the environment, so his data must be wrong.
    """

    analysis = await fallacy_agent.analyze_text(text)

    assert isinstance(analysis, FallacyAnalysis)
    assert len(analysis.detected_fallacies) > 0

    # Should detect ad hominem
    ad_hominem = next(
        (
            f
            for f in analysis.detected_fallacies
            if f.fallacy_type.lower() == "ad hominem"
        ),
        None,
    )
    assert ad_hominem is not None
    assert ad_hominem.confidence > 0.8
    assert "SUV" in ad_hominem.text_segment


@pytest.mark.asyncio
async def test_analyze_text_with_false_dichotomy(fallacy_agent) -> None:
    """Test detection of false dichotomy fallacy."""
    text = """
    Either we completely ban all fossil fuels immediately, or we don't care about the planet at all.
    There's no middle ground when it comes to saving Earth.
    """

    analysis = await fallacy_agent.analyze_text(text)

    assert isinstance(analysis, FallacyAnalysis)
    false_dichotomy = next(
        (
            f
            for f in analysis.detected_fallacies
            if "dichotomy" in f.fallacy_type.lower()
        ),
        None,
    )
    assert false_dichotomy is not None
    assert false_dichotomy.confidence > 0.8
    assert len(analysis.improvement_suggestions) > 0


@pytest.mark.asyncio
async def test_analyze_text_with_multiple_fallacies(fallacy_agent) -> None:
    """Test detection of multiple fallacies in the same text."""
    text = """
    Everyone is switching to electric vehicles these days, so you should too (bandwagon).
    Besides, if we don't all switch to electric cars right now, the entire planet will be
    uninhabitable within 5 years (slippery slope). And let's be honest, anyone who disagrees
    just isn't educated enough to understand the science (ad hominem).
    """

    analysis = await fallacy_agent.analyze_text(text)

    assert isinstance(analysis, FallacyAnalysis)
    assert len(analysis.detected_fallacies) >= 3

    fallacy_types = [f.fallacy_type.lower() for f in analysis.detected_fallacies]
    assert any("bandwagon" in ft for ft in fallacy_types)
    assert any("slippery slope" in ft for ft in fallacy_types)
    assert any("ad hominem" in ft for ft in fallacy_types)


@pytest.mark.asyncio
async def test_analyze_text_with_context(fallacy_agent) -> None:
    """Test fallacy detection with additional context."""
    text = "This policy will obviously fail because the person proposing it is young."
    context = {
        "document_type": "policy_analysis",
        "audience": "professional",
        "domain": "economics",
    }

    analysis = await fallacy_agent.analyze_text(text, context=context)

    assert isinstance(analysis, FallacyAnalysis)
    assert len(analysis.detected_fallacies) > 0
    assert analysis.overall_reasoning_score < 0.7  # Should be low due to fallacy
    assert len(analysis.major_concerns) > 0


@pytest.mark.asyncio
async def test_get_fallacy_explanation(fallacy_agent) -> None:
    """Test retrieving fallacy explanations."""
    explanation = await fallacy_agent.get_fallacy_explanation("ad_hominem")

    assert explanation is not None
    assert explanation.name == "Ad Hominem"
    assert explanation.category == "relevance"
    assert len(explanation.description) > 0
    assert len(explanation.example) > 0


@pytest.mark.asyncio
async def test_suggest_improvements(fallacy_agent) -> None:
    """Test generating improvement suggestions."""
    fallacies = [
        FallacyInstance(
            fallacy_type="ad hominem",
            confidence=0.9,
            text_segment="His economic theory is wrong because he's never had a real job.",
            explanation="Attacks the person rather than the argument",
        ),
    ]

    text = "His economic theory is wrong because he's never had a real job."
    suggestions = await fallacy_agent.suggest_improvements(text, fallacies)

    assert len(suggestions) > 0
    assert all(isinstance(s, str) for s in suggestions)
    assert all(len(s) > 0 for s in suggestions)


@pytest.mark.asyncio
async def test_analyze_text_without_fallacies(fallacy_agent) -> None:
    """Test analysis of text without logical fallacies."""
    text = """
    Research shows that regular exercise improves cardiovascular health.
    Multiple studies have demonstrated a clear correlation between physical
    activity and reduced risk of heart disease. For example, a recent
    meta-analysis of 50 studies found that people who exercise regularly
    have a 30% lower risk of heart attacks.
    """

    analysis = await fallacy_agent.analyze_text(text)

    assert isinstance(analysis, FallacyAnalysis)
    assert len(analysis.detected_fallacies) == 0
    assert (
        analysis.overall_reasoning_score >= 0.8
    )  # Should be high due to good reasoning


@pytest.mark.asyncio
async def test_multi_agent_code_review(fallacy_agent, tmp_path) -> None:
    """Test interaction between LogicalFallacyAgent and SoftwareDeveloperAgent."""
    # Create a sample Python file with some code
    code_file = tmp_path / "sample.py"
    code = """
def calculate_average(numbers):
    \"\"\"Calculate the average of a list of numbers.\"\"\"
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)  # Potential division by zero!
"""
    code_file.write_text(code)

    # Create a code review comment with potential logical fallacies
    review_comment = """
    This code is completely unsafe and will definitely crash in production.
    The developer who wrote this must be inexperienced because they didn't handle
    empty lists. We should reject this PR immediately and rewrite it from scratch,
    there's no other way to fix this.
    """

    # First, analyze the review comment for logical fallacies
    fallacy_analysis = await fallacy_agent.analyze_text(review_comment)

    # Verify fallacies in the review comment
    assert len(fallacy_analysis.detected_fallacies) > 0
    assert any(
        "dichotomy" in f.fallacy_type.lower()
        for f in fallacy_analysis.detected_fallacies
    )
    assert any(
        "ad hominem" in f.fallacy_type.lower()
        for f in fallacy_analysis.detected_fallacies
    )

    # Generate improvement suggestions that address the actual issues
    suggestions = await fallacy_agent.suggest_improvements(
        review_comment,
        fallacy_analysis.detected_fallacies,
    )

    # Verify suggestions are constructive
    assert len(suggestions) > 0
    assert all(len(s) > 0 for s in suggestions)

    # The suggestions should focus on the technical issues rather than personal attacks
    technical_terms = ["empty list", "validation", "error handling", "edge case"]
    assert any(
        any(term.lower() in s.lower() for term in technical_terms) for s in suggestions
    )

    # Verify that the code file was created with the test code
    assert code_file.exists()
    assert code_file.read_text() == code
