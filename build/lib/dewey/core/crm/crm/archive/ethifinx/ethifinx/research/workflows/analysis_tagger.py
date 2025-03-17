"""
Analysis Tagging Workflow
======================

Provides efficient workflows for tagging and summarizing company analysis data.
Optimizes for token usage and caching by using targeted JSON outputs.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional, TypedDict, Generator
from datetime import datetime
from ..engines.deepseek import DeepSeekEngine, DateTimeEncoder
from ..loaders.duckdb_loader import DuckDBLoader, CompanyData
import json
from dataclasses import dataclass


class AnalysisTags(TypedDict):
    """Structure for analysis tags."""
    concern_level: int  # 1-5 scale
    opportunity_score: int  # 1-5 scale
    interest_level: int  # 1-5 scale
    source_reliability: int  # 1-5 scale
    key_concerns: List[str]  # Main ethical concerns
    key_opportunities: List[str]  # Main opportunities
    confidence_score: float  # 0-1 scale
    primary_themes: List[str]  # Main thematic tags


class AnalysisSummary(TypedDict):
    """Structure for condensed analysis summary."""
    key_findings: str  # One-paragraph summary
    main_risks: str  # Bullet-point format
    main_opportunities: str  # Bullet-point format
    recommendation: str  # One-sentence recommendation
    next_steps: str  # Short list of recommended actions


@dataclass
class OpportunityAnalysis:
    """Analysis of potential opportunities from an exploitative perspective."""
    opportunities: List[Dict[str, Any]]  # List of opportunities with details
    total_value_estimate: float          # Estimated value in millions
    ethical_concerns: List[str]          # Ethical concerns for each opportunity
    implementation_risks: List[str]      # Potential risks in implementation


@dataclass
class StrategicQuestions:
    """Deep strategic questions about the organization."""
    questions: List[str]                 # The actual questions
    context: str                         # Why these questions matter
    expected_insights: List[str]         # What insights we hope to gain


@dataclass
class ImpactAssessment:
    """Assessment of revenue to positive impact correlation."""
    correlation_score: float             # 0-1 score
    confidence_rating: float             # 0-1 rating
    supporting_evidence: List[str]       # Evidence for positive correlation
    counterpoints: List[str]             # Evidence against correlation
    key_impact_metrics: List[str]        # Specific measurable impacts


@dataclass
class MaterialTrends:
    """Material trends affecting the company."""
    trends: List[Dict[str, Any]]         # List of trends with details
    impact_timeframe: str                # Short/medium/long term
    probability: float                   # 0-1 probability of trend impact
    potential_disruption: str            # Low/medium/high


class AnalysisTaggingWorkflow:
    """
    Workflow for efficient analysis tagging and summarization.

    Features:
    - Token-efficient JSON outputs
    - Targeted single-purpose prompts
    - Context caching optimization
    - Structured data output
    - DuckDB integration
    """

    def __init__(self, engine: DeepSeekEngine, loader: Optional[DuckDBLoader] = None):
        """Initialize the workflow.
        
        Args:
            engine: DeepSeek engine for analysis
            loader: Optional DuckDB loader. Will create one if not provided.
        """
        self.engine = engine
        self.loader = loader or DuckDBLoader()
        self._init_templates()

    def _init_templates(self) -> None:
        """Initialize specialized JSON output templates."""
        # Template for extracting tags
        self.engine.add_template(
            "tag_extractor",
            [
                {
                    "role": "system",
                    "content": """You are a precise analysis tagger that ONLY outputs valid JSON.
Your response must be a JSON object with the following structure:

{
    "concern_level": 1-5 integer representing level of ethical concerns,
    "opportunity_score": 1-5 integer representing business opportunities,
    "interest_level": 1-5 integer representing overall interest,
    "source_reliability": 1-5 integer representing data reliability,
    "key_concerns": array of strings listing main ethical concerns,
    "key_opportunities": array of strings listing main opportunities,
    "confidence_score": 0-1 float representing confidence level,
    "primary_themes": array of strings listing main thematic tags
}

Do not include any explanatory text or comments. Return ONLY the JSON object."""
                }
            ],
        )

        # Template for creating summaries
        self.engine.add_template(
            "summarizer",
            [
                {
                    "role": "system",
                    "content": """You are a concise analysis summarizer that ONLY outputs valid JSON.
Your response must be a JSON object with the following structure:

{
    "key_findings": "One clear paragraph summarizing key points",
    "main_risks": "Bullet-pointed list of main risks",
    "main_opportunities": "Bullet-pointed list of main opportunities",
    "recommendation": "One clear sentence recommendation",
    "next_steps": "Bullet-pointed list of recommended actions"
}

Do not include any explanatory text or comments. Return ONLY the JSON object."""
                }
            ],
        )

    def prepare_analysis_text(self, company_data: CompanyData) -> str:
        """Prepare the analysis text from company data.
        
        Args:
            company_data: Company data to analyze
            
        Returns:
            Formatted analysis text
        """
        return f"""Company: {company_data.name} ({company_data.ticker})

Previous Analysis Summary:
{company_data.research_results.get('summary', 'No previous research summary available') if company_data.research_results else 'No previous research available'}

Previous Risk Assessment:
Risk Score: {company_data.research_results.get('risk_score', 'N/A') if company_data.research_results else 'N/A'}
Confidence Score: {company_data.research_results.get('confidence_score', 'N/A') if company_data.research_results else 'N/A'}
Previous Recommendation: {company_data.research_results.get('recommendation', 'N/A') if company_data.research_results else 'N/A'}

Raw Research Data:
{json.dumps(company_data.research_results.get('raw_results', []), indent=2) if company_data.research_results and company_data.research_results.get('raw_results') else 'No raw research data available'}

Research Queries and Rationale:
{json.dumps(company_data.research_results.get('search_queries', []), indent=2) if company_data.research_results and company_data.research_results.get('search_queries') else 'No search queries available'}

Source Categories:
{json.dumps(company_data.research_results.get('source_categories', []), indent=2) if company_data.research_results and company_data.research_results.get('source_categories') else 'No source categories available'}

Tick Analysis:
Current Tick: {company_data.current_tick}
Recent History: {', '.join(f"{h['date'].isoformat() if isinstance(h['date'], datetime) else h['date']}: {h['old_tick']} -> {h['new_tick']}" for h in company_data.tick_history[:5])}

Analysis Instructions:
1. Review the previous analysis and raw research data
2. Challenge any assumptions or conclusions from the previous analysis
3. Identify any new insights or patterns from the raw research data
4. Consider if tick changes suggest evolving risks or opportunities
5. Evaluate if the confidence level should be adjusted based on data quality
6. Propose specific actions or monitoring points if warranted
7. Flag any potential biases or gaps in the analysis
"""

    async def extract_tags(
        self, analysis_text: str, context: Optional[Dict[str, Any]] = None
    ) -> AnalysisTags:
        """Extract structured tags from analysis text.
        
        Args:
            analysis_text: Text to analyze
            context: Optional additional context
            
        Returns:
            Structured analysis tags
        """
        prompt = f"""Analyze this text and extract key metrics and tags. Return ONLY a valid JSON object matching the required schema.

Text to analyze:
{analysis_text}"""

        response = await self.engine.json_completion(
            messages=[
                *self.engine.get_template("tag_extractor"),
                {"role": "user", "content": prompt},
            ],
            max_tokens=1000
        )

        if response["error"]:
            raise ValueError(f"Tag extraction failed: {response['error']}")

        try:
            content = response["content"].strip()
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON object found in response")
            json_str = content[json_start:json_end]
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse response as JSON: {str(e)}\nResponse: {content}")

    async def create_summary(
        self, analysis_text: str, tags: Optional[AnalysisTags] = None
    ) -> AnalysisSummary:
        """Create a condensed summary of the analysis.
        
        Args:
            analysis_text: Text to summarize
            tags: Optional tags to incorporate
            
        Returns:
            Structured analysis summary
        """
        context = ""
        if tags:
            context = f"""Analysis Tags:
- Concern Level: {tags['concern_level']}/5
- Opportunity Score: {tags['opportunity_score']}/5
- Interest Level: {tags['interest_level']}/5
- Source Reliability: {tags['source_reliability']}/5
- Confidence: {tags['confidence_score']}
- Key Themes: {', '.join(tags['primary_themes'])}"""

        prompt = f"""Create a structured summary of this analysis. Return ONLY a valid JSON object matching the required schema.

{context}

Text to analyze:
{analysis_text}"""

        response = await self.engine.json_completion(
            messages=[
                *self.engine.get_template("summarizer"),
                {"role": "user", "content": prompt},
            ],
            max_tokens=2000
        )

        if response["error"]:
            raise ValueError(f"Summary creation failed: {response['error']}")

        try:
            content = response["content"].strip()
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON object found in response")
            json_str = content[json_start:json_end]
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse response as JSON: {str(e)}\nResponse: {content}")

    async def process_analysis(
        self,
        company_data: CompanyData,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process company data to extract tags and create summary.
        
        Args:
            company_data: Company data from loader
            context: Optional additional context
            
        Returns:
            Combined tags and summary data
        """
        # Prepare analysis text
        analysis_text = self.prepare_analysis_text(company_data)

        # Extract tags first
        tags = await self.extract_tags(analysis_text, context)

        # Create summary using tags
        summary = await self.create_summary(analysis_text, tags)

        return {
            "ticker": company_data.ticker,
            "timestamp": datetime.now().isoformat(),
            "tags": tags,
            "summary": summary,
            "metadata": {
                "text_length": len(analysis_text),
                "context_used": bool(context),
                "processing_version": "1.0",
                "current_tick": company_data.current_tick,
                "last_tick_update": company_data.meta.get('last_tick_update')
            },
        }

    async def process_companies_by_tick_range(
        self,
        min_tick: int,
        max_tick: int,
        limit: Optional[int] = None,
        callback: Optional[callable] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """Process all companies within a tick range.
        
        Args:
            min_tick: Minimum tick value (inclusive)
            max_tick: Maximum tick value (inclusive)
            limit: Optional limit on number of companies to process
            callback: Optional callback function to call after each company is processed
            
        Yields:
            Analysis results for each company
        """
        for company in self.loader.load_companies_by_tick_range(min_tick, max_tick, limit):
            try:
                result = await self.process_analysis(company)
                
                # Save results back to database
                self.loader.save_research_results(company.ticker, {
                    'summary': result['summary']['key_findings'],
                    'risk_score': result['tags']['concern_level'],
                    'confidence_score': int(result['tags']['confidence_score'] * 100),
                    'recommendation': result['summary']['recommendation'],
                    'structured_data': json.loads(json.dumps(result['tags'], cls=DateTimeEncoder)),
                    'source_categories': result['summary'].get('main_risks'),
                    'meta_info': json.loads(json.dumps(result['metadata'], cls=DateTimeEncoder))
                })
                
                if callback:
                    callback(result)
                
                yield result
            except Exception as e:
                yield {
                    "ticker": company.ticker,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }

    async def process_companies_by_tickers(
        self,
        tickers: List[str],
        callback: Optional[callable] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """Process specific companies by their tickers.
        
        Args:
            tickers: List of company tickers to process
            callback: Optional callback function to call after each company is processed
            
        Yields:
            Analysis results for each company
        """
        for company in self.loader.load_companies_by_tickers(tickers):
            try:
                result = await self.process_analysis(company)
                
                # Save results back to database
                self.loader.save_research_results(company.ticker, {
                    'summary': result['summary']['key_findings'],
                    'risk_score': result['tags']['concern_level'],
                    'confidence_score': int(result['tags']['confidence_score'] * 100),
                    'recommendation': result['summary']['recommendation'],
                    'structured_data': json.loads(json.dumps(result['tags'], cls=DateTimeEncoder)),
                    'source_categories': result['summary'].get('main_risks'),
                    'meta_info': json.loads(json.dumps(result['metadata'], cls=DateTimeEncoder))
                })
                
                if callback:
                    callback(result)
                
                yield result
            except Exception as e:
                yield {
                    "ticker": company.ticker,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                }

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Run analysis tagger workflow")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tickers", help="Comma-separated list of tickers to analyze")
    group.add_argument("--tick-range", help="Tick range to analyze (min-max)")
    parser.add_argument("--limit", type=int, help="Limit number of companies to process")
    args = parser.parse_args()
    
    async def main():
        engine = DeepSeekEngine(os.getenv("DEEPSEEK_API_KEY"))
        workflow = AnalysisTaggingWorkflow(engine)
        
        def print_result(result: Dict[str, Any]) -> None:
            if "error" in result:
                print(f"❌ Error processing {result['ticker']}: {result['error']}")
            else:
                print(f"✅ {result['ticker']}:")
                print(f"  Risk: {result['tags']['concern_level']}/5")
                print(f"  Confidence: {result['tags']['confidence_score']:.2f}")
                print(f"  Themes: {', '.join(result['tags']['primary_themes'][:3])}")
                print(f"  Recommendation: {result['summary']['recommendation']}\n")
        
        if args.tickers:
            tickers = [t.strip() for t in args.tickers.split(",")]
            async for result in workflow.process_companies_by_tickers(tickers, callback=print_result):
                pass
        else:
            min_tick, max_tick = map(int, args.tick_range.split("-"))
            async for result in workflow.process_companies_by_tick_range(min_tick, max_tick, args.limit, callback=print_result):
                pass
    
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
