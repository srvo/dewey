from typing import Dict, List, Optional
import asyncio
from datetime import datetime
import re
from tqdm import tqdm
import aiohttp
import json
import logging
import time
import hashlib
from pathlib import Path
from functools import lru_cache

class EnhancedSearchClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url
        self.api_key = api_key
        self.session = aiohttp.ClientSession()
        # Add rate limiting
        self.request_interval = 20  # seconds between requests
        self.last_request_time = 0
        self.semaphore = asyncio.Semaphore(3)  # limit concurrent requests
        
        # Setup logging
        self.logger = logging.getLogger('enhanced_search')
        
    async def search(self, query: str, provider: str = "searxng", max_retries: int = 3) -> Dict:
        """Perform search using the chat endpoint with SSE support, retries, and rate limiting"""
        for attempt in range(max_retries):
            try:
                # Wait for rate limit
                now = time.time()
                if now - self.last_request_time < self.request_interval:
                    wait_time = self.request_interval - (now - self.last_request_time)
                    self.logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                self.last_request_time = time.time()

                async with self.semaphore:  # Control concurrent requests
                    self.logger.info(f"Sending query for {query[:30]}...")
                    async with self.session.post(
                        f"{self.base_url}/chat",
                        json={
                            "query": query,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": """You are a financial analyst assistant. Analyze the given company/stock and provide a detailed analysis in the following format:

### Market Intelligence
1. Recent Financial Performance
   - Latest quarterly results
   - Revenue trends
   - Key metrics and ratios

2. Market Position & Competition
   - Industry standing
   - Competitive advantages
   - Market share trends

3. Risk Assessment
   - Industry-specific challenges
   - Regulatory environment
   - Financial risks

4. Strategic Outlook
   - Growth initiatives
   - Future opportunities
   - Innovation pipeline

Be specific, factual, and concise. Focus on recent developments and data."""
                                },
                                {
                                    "role": "user",
                                    "content": f"Provide a detailed analysis of {query}. Focus on recent developments, financial metrics, and market position."
                                }
                            ],
                            "temperature": 0.7,
                            "model": "gpt-4o"
                        }
                    ) as response:
                        if response.status == 200:
                            self.logger.debug("Got 200 response, reading stream...")
                            # Handle SSE stream
                            full_response = []
                            current_chunk = ""
                            async for line in response.content:
                                line = line.decode('utf-8').strip()
                                if line:  # Only process non-empty lines
                                    if line.startswith('data: '):
                                        data = line[6:].strip()  # Remove 'data: ' prefix
                                        if data == '[DONE]':
                                            continue
                                        try:
                                            # Try to parse as JSON to extract actual content
                                            json_data = json.loads(data)
                                            if 'data' in json_data and 'text' in json_data['data']:
                                                text = json_data['data']['text']
                                                if text and not text.isspace():
                                                    current_chunk += text
                                        except json.JSONDecodeError:
                                            # If not JSON, just append the raw text if it's not event-related
                                            if not any(event in data.lower() for event in ['event:', 'begin-stream', 'search-results', 'final-response']):
                                                current_chunk += data
                                        print(".", end="", flush=True)
                            
                            if current_chunk:
                                # Clean up the response
                                current_chunk = current_chunk.strip()
                                if current_chunk:
                                    full_response.append(current_chunk)
                            
                            self.logger.debug("Finished reading stream")
                            complete_response = "\n".join(full_response)
                            if complete_response:
                                return {"results": [{"content": complete_response}]}
                            else:
                                self.logger.warning("Empty response received")
                                return {"error": "Empty response"}
                        else:
                            self.logger.error(f"Search failed with status {response.status}")
                            self.logger.error(f"Response: {await response.text()}")
                            raise Exception(f"Search failed with status {response.status}")

            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"Final retry failed: {str(e)}")
                    return {"error": str(e)}
                wait_time = (2 ** attempt) * 5  # exponential backoff
                self.logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                await asyncio.sleep(wait_time)
            
    async def close(self):
        if self.session:
            await self.session.close()

class DeepAnalysisEngine:
    def __init__(self, report_path: str, questions_template: str, api_url: str = "http://localhost:8000"):
        self.report_path = report_path
        self.questions = self._parse_questions(questions_template)
        self.client = EnhancedSearchClient(base_url=api_url)
        
        # Setup caching
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_file = self.cache_dir / "analysis_cache.json"
        self.cache = self._load_cache()
        
        # Setup logging
        self.logger = self._setup_logging()
        
    def _setup_logging(self):
        logger = logging.getLogger('deep_analysis')
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # File handler
        fh = logging.FileHandler(logs_dir / f'deep_analysis_{datetime.now():%Y%m%d}.log')
        fh.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        return logger
        
    def _load_cache(self) -> Dict:
        """Load the analysis cache from disk"""
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save_cache(self):
        """Save the analysis cache to disk"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f)
        
    def _load_report(self) -> str:
        """Load the existing stock analysis report"""
        self.logger.info(f"Loading report from: {self.report_path}")
        try:
            with open(self.report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.logger.info(f"Successfully loaded report ({len(content)} characters)")
            if not content.strip():
                self.logger.warning("Report file is empty")
                content = "# Stock Analysis Report\n\nGenerated at: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return content
        except Exception as e:
            self.logger.error(f"Error loading report: {e}")
            return ""

    def _split_sections(self, content: str) -> List[str]:
        """Split report into sections by company"""
        sections = []
        current_section = []
        
        for line in content.split('\n'):
            if line.startswith('## '):  # Start of new company section
                if current_section:  # Save previous section if exists
                    sections.append('\n'.join(current_section))
                current_section = [line]  # Start new section
            else:
                current_section.append(line)
        
        # Add the last section
        if current_section:
            sections.append('\n'.join(current_section))
            
        return sections

    def _extract_symbol(self, section: str) -> Optional[str]:
        """Extract company symbol from section header"""
        match = re.search(r'## ([A-Z]+)', section)
        return match.group(1) if match else None

    async def _expert_search(self, query: str) -> Dict:
        """Perform an expert search using Farfalle's capabilities with caching"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        
        # Check cache first
        if query_hash in self.cache:
            self.logger.debug(f"Cache hit for query: {query[:30]}...")
            return self.cache[query_hash]
        
        # Perform search if not in cache
        self.logger.debug(f"Cache miss for query: {query[:30]}...")
        results = await self.client.search(query, provider="searxng")
        
        # Cache successful results
        if "error" not in results:
            self.cache[query_hash] = results
            self._save_cache()
            
        return results

    async def enhance_report(self) -> str:
        """Enhance the existing stock analysis report with deep insights"""
        report_content = self._load_report()
        sections = self._split_sections(report_content)
        
        self.logger.info(f"Found {len(sections)} sections to process")
        
        # Load checkpoint if exists
        checkpoint_file = Path(f"{self.report_path}.checkpoint")
        try:
            with open(checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                enhanced_sections = checkpoint['sections']
                last_processed = checkpoint['last_processed']
                self.logger.info(f"Loaded checkpoint, resuming from section {last_processed + 1}")
        except:
            enhanced_sections = []
            last_processed = -1
            self.logger.info("No checkpoint found, starting from beginning")
        
        # Process in batches of 5 to control memory usage
        batch_size = 5
        
        for i in range(last_processed + 1, len(sections), batch_size):
            batch = sections[i:i + batch_size]
            tasks = []
            
            self.logger.info(f"Processing batch {i//batch_size + 1} of {(len(sections) + batch_size - 1)//batch_size}")
            
            for section in batch:
                symbol = self._extract_symbol(section)
                if symbol:
                    tasks.append(self._enhance_stock_section(section, symbol))
            
            # Process batch concurrently with progress tracking
            with tqdm(total=len(batch), desc=f"Batch {i//batch_size + 1}") as pbar:
                batch_results = await asyncio.gather(*tasks)
                enhanced_sections.extend(batch_results)
                pbar.update(len(batch))
            
            # Save checkpoint after each batch
            with open(checkpoint_file, 'w') as f:
                json.dump({
                    'sections': enhanced_sections,
                    'last_processed': i + len(batch) - 1
                }, f)
            
            self.logger.info(f"Saved checkpoint after batch {i//batch_size + 1}")
        
        # Combine sections back together with proper spacing
        enhanced_report = '\n\n'.join(section.strip() for section in enhanced_sections if section.strip())
        
        # Clean up checkpoint file after successful completion
        checkpoint_file.unlink(missing_ok=True)
        
        await self.client.close()
        return enhanced_report

    async def _enhance_stock_section(self, section: str, symbol: str) -> str:
        """Add deep analysis to a stock section using Farfalle search"""
        await asyncio.sleep(1)  # Add delay before search
        self.logger.info(f"Processing {symbol}...")
        
        # First perform expert search for additional insights
        query = f"{symbol} stock analysis market position strategic outlook risk factors recent developments"
        results = await self._expert_search(query)
        
        if "error" in results:
            self.logger.error(f"Error for {symbol}, using fallback analysis")
            return section
            
        # Clean up the existing section
        enhanced_section = section.rstrip()
        
        # Add insights from the search
        if results.get("results"):
            content = results["results"][0].get("content", "").strip()
            if content:
                # Add a newline before the Market Intelligence section if it doesn't start with it
                if not content.startswith('### Market Intelligence'):
                    content = '\n### Market Intelligence\n' + content
                enhanced_section += '\n\n' + content
                self.logger.info(f"Added insights for {symbol}")
            else:
                self.logger.warning(f"No content in results for {symbol}")
        else:
            self.logger.warning(f"No results found for {symbol}")
        
        return enhanced_section

    def _parse_questions(self, template: str) -> Dict[str, Dict[str, List[str]]]:
        """Parse questions template to extract categories and follow-up prompts"""
        try:
            with open(template, 'r') as f:
                content = f.read()
            # For now, return empty dict since we're not using the questions directly
            return {}
        except Exception as e:
            self.logger.warning(f"Could not parse questions template: {e}")
            return {}

async def main():
    report_path = "/Users/srvo/local/stock_analysis_report_20241228_190624.md"
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting deep analysis on report: {report_path}")
    
    # Initialize engine
    engine = DeepAnalysisEngine(
        report_path=report_path,
        questions_template="/Users/srvo/local/questions.md",
        api_url="http://localhost:8000"
    )
    
    try:
        # Load existing report
        existing_content = engine._load_report()
        
        # Extract existing symbols
        existing_symbols = set(re.findall(r'## ([A-Z]+)', existing_content))
        logger.info(f"Found {len(existing_symbols)} existing stocks: {', '.join(sorted(existing_symbols))}")
        
        # New stocks to analyze
        new_stocks = ["NVDA", "TSLA", "AMD", "INTC", "ORCL"]
        stocks_to_add = [s for s in new_stocks if s not in existing_symbols]
        
        if not stocks_to_add:
            logger.info("No new stocks to add")
            return
            
        logger.info(f"Adding {len(stocks_to_add)} new stocks: {', '.join(stocks_to_add)}")
        
        # Append new stocks to existing content
        updated_content = existing_content.rstrip() + "\n\n"  # Ensure proper spacing
        for symbol in stocks_to_add:
            updated_content += f"## {symbol}\n\n"
        
        # Write updated content
        with open(report_path, "w", encoding='utf-8') as f:
            f.write(updated_content)
            f.flush()
        
        logger.info(f"Updated report with new stocks")
        
        # Enhance report
        logger.info("Loading and enhancing report...")
        enhanced_report = await engine.enhance_report()
        
        logger.info(f"Writing enhanced report to: {report_path}")
        logger.info(f"Report length: {len(enhanced_report)} characters")
        
        # Write the enhanced report
        with open(report_path, "w", encoding='utf-8') as f:
            f.write(enhanced_report)
            f.flush()
        
        logger.info("Successfully wrote enhanced report to file")
        
    except Exception as e:
        logger.error(f"Error during report enhancement: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 