import os
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel
import dlt
import pandas as pd
from dotenv import load_dotenv
import logging

# Set up logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "api_rate_limits.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get GitHub token
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

class RateLimitMonitor:
    """Simple rate limit monitoring with threshold alerts"""
    def __init__(self):
        self._limits = {}
        self.thresholds = [10, 20, 30, 40, 50, 60, 70, 80, 90]  # Percentage thresholds
    
    def update_limit(self, api_name: str, remaining: int, limit: int):
        """Update rate limit info and log if threshold is crossed"""
        if api_name not in self._limits:
            self._limits[api_name] = {'last_threshold': -1}
        
        usage_percent = 100 - (remaining / limit * 100)
        crossed_threshold = next((t for t in self.thresholds 
                                if usage_percent >= t > self._limits[api_name]['last_threshold']), None)
        
        if crossed_threshold:
            logger.warning(
                f"{api_name} API usage at {crossed_threshold}% "
                f"({remaining}/{limit} requests remaining)"
            )
            self._limits[api_name]['last_threshold'] = crossed_threshold
        
        self._limits[api_name].update({
            'remaining': remaining,
            'limit': limit,
            'last_check': datetime.now()
        })

class LibraryMetrics(BaseModel):
    """Metrics for a library"""
    name: str
    description: str
    url: str
    stars: Optional[int]
    forks: Optional[int]
    open_issues: Optional[int]
    closed_issues: Optional[int]
    contributors: Optional[int]
    commits_last_year: Optional[int]
    documentation_score: Optional[float]
    test_coverage: Optional[float]
    dependencies: Optional[List[str]]
    license: Optional[str]
    latest_release: Optional[str]
    release_frequency: Optional[float]  # releases per month
    code_velocity: Optional[float]  # commits per week
    issue_resolution_rate: Optional[float]  # percentage of closed issues

class APIClient:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.rate_monitor = RateLimitMonitor()
    
    async def request(self, method: str, url: str, api_name: str, **kwargs):
        """Make an API request with simple rate limit monitoring"""
        async with self.session.request(method, url, **kwargs) as response:
            # Update rate limits from headers
            remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
            limit = int(response.headers.get('X-RateLimit-Limit', 0))
            
            if limit > 0:  # Only track if rate limit headers are present
                self.rate_monitor.update_limit(api_name, remaining, limit)
            
            if response.status == 429:  # Too Many Requests
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.error(
                    f"Rate limit exceeded for {api_name}. "
                    f"Waiting {retry_after} seconds."
                )
                await asyncio.sleep(retry_after)
                return await self.request(method, url, api_name, **kwargs)
            
            return await response.json()

async def analyze_github_repo(client: APIClient, repo_url: str) -> Dict:
    """Analyze a GitHub repository for various metrics"""
    if not repo_url or 'github.com' not in repo_url:
        return {}
    
    try:
        # Extract owner and repo from URL
        parts = repo_url.rstrip('/').split('/')
        if len(parts) < 5:
            return {}
        owner, repo = parts[-2], parts[-1]
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        
        # Fetch basic repo info
        repo_data = await client.request('GET', api_url, 'github')
        
        # Fetch commit activity
        commit_data = await client.request('GET', f"{api_url}/stats/commit_activity", 'github')
        
        # Fetch closed issues count
        issues_data = await client.request('GET', f"{api_url}/issues?state=closed&per_page=1", 'github')
        closed_issues = int(issues_data.get('total_count', 0))
        
        # Calculate code velocity (commits per week)
        recent_commits = sum(week.get('total', 0) for week in commit_data[-4:]) if commit_data else 0
        code_velocity = recent_commits / 4 if commit_data else 0
        
        # Calculate issue resolution rate
        total_issues = repo_data.get('open_issues_count', 0) + closed_issues
        issue_resolution_rate = (closed_issues / total_issues * 100) if total_issues > 0 else 0
        
        # Analyze documentation quality
        doc_score = await analyze_documentation_quality(client, api_url)
        
        # Analyze test coverage
        test_coverage = await analyze_test_coverage(client, api_url)
        
        return {
            'stars': repo_data.get('stargazers_count'),
            'forks': repo_data.get('forks_count'),
            'open_issues': repo_data.get('open_issues_count'),
            'closed_issues': closed_issues,
            'contributors': repo_data.get('subscribers_count'),
            'commits_last_year': sum(week.get('total', 0) for week in commit_data) if commit_data else None,
            'documentation_score': doc_score,
            'test_coverage': test_coverage,
            'license': repo_data.get('license', {}).get('name'),
            'latest_release': repo_data.get('pushed_at'),
            'code_velocity': code_velocity,
            'issue_resolution_rate': issue_resolution_rate
        }
    except Exception as e:
        logger.error(f"Error analyzing repo {repo_url}: {e}")
        return {}

async def analyze_documentation_quality(client: APIClient, api_url: str) -> float:
    """Analyze documentation quality based on various factors"""
    try:
        score = 0.0
        max_score = 5.0
        
        # Check for key documentation files
        doc_files = {
            'README.md': 1.0,
            'CONTRIBUTING.md': 0.5,
            'API.md': 0.5,
            'docs/': 1.0,
            'examples/': 1.0,
            'CHANGELOG.md': 0.5,
            'LICENSE': 0.5
        }
        
        for file_name, points in doc_files.items():
            try:
                response = await client.request('GET', f"{api_url}/contents/{file_name}", 'github')
                if response:
                    score += points
            except:
                continue
        
        return (score / max_score) * 100
    except Exception as e:
        logger.error(f"Error analyzing documentation quality: {e}")
        return 0.0

async def analyze_test_coverage(client: APIClient, api_url: str) -> float:
    """Analyze test coverage based on repository contents"""
    try:
        # Get repository contents
        contents = await client.request('GET', f"{api_url}/contents", 'github')
        
        # Look for test files
        test_files = [f for f in contents if 'test' in f['name'].lower() or 'spec' in f['name'].lower()]
        if not test_files:
            return 0.0
        
        # Look for coverage reports
        try:
            coverage_data = await client.request('GET', f"{api_url}/contents/.coverage", 'github')
            if coverage_data:
                return float(coverage_data.get('content', 0))
        except:
            pass
        
        # Estimate based on test files ratio
        return min(len(test_files) / len(contents) * 100, 100.0)
    except Exception as e:
        logger.error(f"Error analyzing test coverage: {e}")
        return 0.0

async def extract_library_info(markdown_content: str) -> List[Dict]:
    """Extract library information from markdown content"""
    libraries = []
    lines = markdown_content.split('\n')
    
    for line in lines:
        if '|' not in line:
            continue
        
        # Skip header and separator lines
        if '**Library Name**' in line or '---' in line:
            continue
        
        parts = line.split('|')
        if len(parts) >= 4:
            name = parts[1].strip()
            description = parts[2].strip()
            url = parts[3].strip()
            
            # Extract URL from markdown link format [text](url)
            if '[' in url and ']' in url and '(' in url and ')' in url:
                url = url[url.find('(')+1:url.find(')')]
            
            if name and description and url:
                libraries.append({
                    'name': name,
                    'description': description,
                    'url': url
                })
    
    return libraries

async def main():
    # Read the markdown file
    try:
        with open('libraries_and_resources.md', 'r') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Error reading markdown file: {e}")
        return
    
    # Extract library information
    libraries = await extract_library_info(content)
    
    # Create pipeline for storing data
    pipeline = dlt.pipeline(
        pipeline_name="library_metrics",
        destination='duckdb',
        dataset_name='library_analytics'
    )
    
    # Create session with auth headers
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        client = APIClient(session)
        enriched_data = []
        
        for lib in libraries:
            try:
                metrics = await analyze_github_repo(client, lib['url'])
                if metrics:
                    enriched_data.append({
                        **lib,
                        **metrics
                    })
            except Exception as e:
                logger.error(f"Error processing library {lib['name']}: {e}")
                continue
        
        # Store data in DuckDB
        df = pd.DataFrame(enriched_data)
        pipeline.run(
            df,
            table_name="library_metrics",
            write_disposition="replace"
        )
        
        # Generate summary statistics
        with pipeline.sql_client() as client:
            summary = client.query("""
                SELECT 
                    COUNT(*) as total_libraries,
                    AVG(stars) as avg_stars,
                    AVG(documentation_score) as avg_doc_score,
                    AVG(test_coverage) as avg_test_coverage,
                    AVG(code_velocity) as avg_code_velocity,
                    AVG(issue_resolution_rate) as avg_issue_resolution_rate
                FROM library_metrics
            """)
            
            print("\nLibrary Ecosystem Summary:")
            print(summary)
            
            # Top libraries by overall quality
            top_libraries = client.query("""
                SELECT 
                    name,
                    stars,
                    documentation_score,
                    test_coverage,
                    code_velocity,
                    issue_resolution_rate
                FROM library_metrics
                WHERE documentation_score > 0 
                    AND test_coverage > 0
                ORDER BY (
                    COALESCE(documentation_score, 0) + 
                    COALESCE(test_coverage, 0) + 
                    COALESCE(code_velocity * 10, 0) + 
                    COALESCE(issue_resolution_rate, 0)
                ) DESC
                LIMIT 10
            """)
            
            print("\nTop 10 Libraries by Overall Quality:")
            print(top_libraries)

if __name__ == "__main__":
    asyncio.run(main()) 