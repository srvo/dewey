"""
DeepSeek Engine

A research engine implementation using the DeepSeek AI model for analysis.
"""

import os
import json
import logging
import aiohttp
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class DeepSeekEngine:
    """Engine for processing company information using DeepSeek LLM."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the DeepSeek engine.

        Args:
            api_key: The API key for DeepSeek API access.
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-chat"

    async def analyze_company(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a company using the DeepSeek engine.

        Args:
            company_data: Dictionary containing company information

        Returns:
            Dictionary containing analysis results
        """
        try:
            # Extract company information
            ticker = company_data.get("ticker", "Unknown")
            name = company_data.get("name", "Unknown")
            description = company_data.get("description", "")
            sector = company_data.get("sector", "")
            industry = company_data.get("industry", "")
            
            # Build prompt for the LLM
            prompt = self._build_analysis_prompt(ticker, name, description, sector, industry)
            
            # Get analysis from DeepSeek
            analysis = await self._call_deepseek_api(prompt)
            
            # Process and return the results
            return {
                "ticker": ticker,
                "name": name,
                "analysis": analysis,
                "success": True
            }
        except Exception as e:
            logger.error(f"Error analyzing company {company_data.get('ticker', 'unknown')}: {str(e)}")
            return {
                "ticker": company_data.get("ticker", "Unknown"),
                "name": company_data.get("name", "Unknown"),
                "error": str(e),
                "success": False
            }

    def _build_analysis_prompt(
        self, ticker: str, name: str, description: str, sector: str, industry: str
    ) -> str:
        """Build a prompt for company analysis.

        Args:
            ticker: Company ticker symbol
            name: Company name
            description: Company description
            sector: Company sector
            industry: Company industry

        Returns:
            Formatted prompt string
        """
        return f"""
        Please analyze the following company for ethical and financial risks:

        Company: {name} ({ticker})
        Sector: {sector}
        Industry: {industry}
        Description: {description}

        Please include the following in your analysis:
        1. Ethical concerns (environmental, social, governance)
        2. Financial risk assessment
        3. Overall concern level on a scale of 1-5
        4. Confidence in analysis (0.0-1.0)
        5. Primary themes to monitor
        6. Recommendation (avoid, monitor, safe)
        7. Brief summary

        Format your response as JSON with the following structure:
        {{
            "tags": {{
                "concern_level": int,
                "confidence_score": float,
                "primary_themes": [list of strings]
            }},
            "summary": {{
                "recommendation": string,
                "summary": string
            }}
        }}
        """

    async def _call_deepseek_api(self, prompt: str) -> Dict[str, Any]:
        """Call the DeepSeek API with the given prompt.

        Args:
            prompt: The prompt to send to the DeepSeek API

        Returns:
            The parsed JSON response from the API

        Raises:
            Exception: If the API call fails
        """
        if not self.api_key:
            # For demo/testing purposes, return a mock response
            return self._get_mock_response()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are an expert in ethical and financial analysis of companies."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url, 
                    headers=headers, 
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                        return json.loads(content)
                    else:
                        error_text = await response.text()
                        raise Exception(f"API error ({response.status}): {error_text}")
        except json.JSONDecodeError:
            raise Exception("Failed to parse API response")
        except Exception as e:
            raise Exception(f"API call failed: {str(e)}")
    
    def _get_mock_response(self) -> Dict[str, Any]:
        """Get a mock response for testing when no API key is available.

        Returns:
            A mock analysis response
        """
        return {
            "tags": {
                "concern_level": 3,
                "confidence_score": 0.85,
                "primary_themes": ["Environmental Impact", "Supply Chain Ethics", "Corporate Governance"]
            },
            "summary": {
                "recommendation": "monitor",
                "summary": "This company has moderate ethical concerns primarily around environmental practices and supply chain management. Financial risk is average for the industry. Recommend monitoring developments in sustainability initiatives and governance changes."
            }
        } 