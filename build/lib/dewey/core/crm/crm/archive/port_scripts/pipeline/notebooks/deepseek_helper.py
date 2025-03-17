from typing import Dict, List, Any, Optional
import re
from dataclasses import dataclass
from openai import OpenAI
from collections import defaultdict
import time
import json
import httpx
from scrapling import Adaptor as Scrapling
from traceback import print_exc, format_exc
import sys
import asyncio
from datetime import datetime

@dataclass
class FunctionMetadata:
    keywords: List[str]
    rate_limit: int
    priority: int
    api_docs_url: Optional[str] = None

class DeepSeekFunctionHelper:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
        """Initialize the DeepSeek helper with API key and base URL."""
        api_key = api_key.strip()
        if not api_key.startswith("Bearer "):
            api_key = f"Bearer {api_key}"
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.scrapling = Scrapling(text="<html></html>")  # Initialize with empty HTML
        self.api_docs_cache = {}  # Use consistent name
        self.functions = []
        self.function_call_counts = defaultdict(int)
        self.last_call_time = defaultdict(float)

    async def fetch_api_docs(self, url: str) -> str:
        """Fetch API documentation using Scrapling.
        
        Args:
            url: The URL of the API documentation to fetch
            
        Returns:
            str: The extracted text from the documentation
        """
        if url in self.api_docs_cache:
            print(f"Using cached documentation for {url}")
            return self.api_docs_cache[url]
        
        try:
            print(f"Fetching API documentation from {url}")
            # Fetch the HTML content first
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                html_content = response.text
            
            # Create a new Scrapling instance with the HTML content
            scraper = Scrapling(text=html_content)
            
            # Configure Scrapling options for better API doc extraction
            scraper.config(
                ignore_links=True,      # We don't need links
                ignore_images=True,      # We don't need images
                clean_spaces=True,       # Clean up whitespace
                remove_selectors=[       # Remove common non-documentation elements
                    'nav',
                    'header',
                    'footer',
                    '.sidebar',
                    '#sidebar',
                    '.menu',
                    '#menu',
                    '.navigation',
                    '.site-header',
                    '.site-footer',
                    '.cookie-banner',
                    '.announcement',
                    '.ads',
                    '.advertisement'
                ],
                keep_selectors=[        # Keep important API documentation elements
                    '.api-docs',
                    '.documentation',
                    '.endpoint-docs',
                    '.method-docs',
                    '.parameters',
                    '.responses',
                    '.examples',
                    '.code-samples',
                    'pre',
                    'code'
                ]
            )
            
            # Get the main content
            text = await scraper.get_text()
            
            # Basic cleaning of the extracted text
            text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
            text = re.sub(r'\n\s*\n', '\n\n', text)  # Replace multiple newlines with double newline
            text = text.strip()
            
            if not text:
                print(f"Warning: No text content extracted from {url}")
                # Try alternative selectors if no content was found
                scraper.config(
                    keep_selectors=[
                        'main',
                        'article',
                        '.content',
                        '.main-content',
                        '.docs-content'
                    ]
                )
                text = await scraper.get_text()
                text = re.sub(r'\s+', ' ', text)
                text = re.sub(r'\n\s*\n', '\n\n', text)
                text = text.strip()
                
                if not text:
                    print(f"Warning: Still no content found with alternative selectors")
                    return ""
            
            # Cache the result
            self.api_docs_cache[url] = text
            print(f"Successfully cached documentation for {url} ({len(text)} characters)")
            return text
            
        except Exception as e:
            print(f"Error fetching API docs from {url}: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            print(f"Stack trace:\n{format_exc()}")
            return ""

    def define_api_functions(self, api_list: List[Dict[str, Any]]) -> None:
        """Define multiple APIs as functions with metadata."""
        self.functions = []
        for api in api_list:
            function_def = {
                "type": "function",
                "function": {
                    "name": api["name"],
                    "description": api["description"],
                    "parameters": api["parameters"],
                    "metadata": api.get("metadata", {
                        "keywords": [],
                        "rate_limit": 100,  # Default rate limit
                        "priority": 1,      # Default priority
                        "api_docs_url": None  # Optional API docs URL
                    })
                }
            }
            self.functions.append(function_def)

    def preprocess_query(self, query: str) -> List[str]:
        """Extract keywords from the query using simple tokenization."""
        # Convert to lowercase and split on non-alphanumeric characters
        tokens = re.findall(r'\w+', query.lower())
        # Remove common stop words (simplified version)
        stop_words = {'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or'}
        return [token for token in tokens if token not in stop_words]

    def filter_functions(self, query_keywords: List[str], min_match_count: int = 1) -> List[Dict]:
        """Filter functions based on keyword matches."""
        relevant_functions = []
        for func in self.functions:
            metadata = func["function"]["metadata"]
            match_count = sum(keyword in metadata["keywords"] for keyword in query_keywords)
            if match_count >= min_match_count:
                relevant_functions.append(func)
        return relevant_functions

    def check_rate_limit(self, func_name: str) -> bool:
        """Check if the function can be called based on rate limits."""
        for func in self.functions:
            if func["function"]["name"] == func_name:
                metadata = func["function"]["metadata"]
                current_time = time.time()
                # Reset count if more than an hour has passed
                if current_time - self.last_call_time[func_name] > 3600:
                    self.function_call_counts[func_name] = 0
                    self.last_call_time[func_name] = current_time
                return self.function_call_counts[func_name] < metadata["rate_limit"]
        return False

    def score_functions(self, query_keywords: List[str]) -> List[Dict]:
        """Score and sort functions based on relevance, priority, and rate limits."""
        scored_functions = []
        for func in self.functions:
            metadata = func["function"]["metadata"]
            match_count = sum(keyword in metadata["keywords"] for keyword in query_keywords)
            remaining_calls = metadata["rate_limit"] - self.function_call_counts[func["function"]["name"]]
            if remaining_calls <= 0:
                continue
            score = (match_count * metadata["priority"]) / (1 + 1/remaining_calls)
            scored_functions.append((func, score))
        
        scored_functions.sort(key=lambda x: x[1], reverse=True)
        return [func for func, _ in scored_functions]

    async def send_query_with_functions(self, messages: List[Dict[str, str]], query: str) -> Dict[str, Any]:
        """Send a query to DeepSeek API with function calling capabilities."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=self.headers,
                    json={
                        "model": "deepseek-chat",
                        "messages": messages,
                        "tools": self.functions
                    }
                )
                response.raise_for_status()
                response_data = response.json()
                
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    message = response_data["choices"][0]["message"]
                    if isinstance(message, dict):
                        return {
                            "content": message.get("content", ""),
                            "source": "DeepSeek Research",
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        return {
                            "content": str(message),
                            "source": "DeepSeek Research",
                            "timestamp": datetime.now().isoformat()
                        }
                
                return {
                    "content": "No response content available",
                    "source": "DeepSeek Research",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            print(f"Error in send_query_with_functions: {str(e)}")
            await self.handle_api_error(e, "send_query_with_functions", query)
            return {
                "content": f"Error: {str(e)}",
                "source": "Error",
                "timestamp": datetime.now().isoformat()
            }

    def update_function_call_count(self, func_name: str) -> None:
        """Update the call count for a function."""
        self.function_call_counts[func_name] += 1
        self.last_call_time[func_name] = time.time()

    async def handle_multiple_functions(self, query: str, messages: List[Dict[str, str]], 
                                      function_handlers: Dict[str, callable]) -> List[Any]:
        """Handle multiple function calls for a single query."""
        query_keywords = self.preprocess_query(query)
        relevant_functions = self.score_functions(query_keywords)
        
        if not relevant_functions:
            return []

        message = await self.send_query_with_functions(messages, query)
        results = []

        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                if func_name in function_handlers and self.check_rate_limit(func_name):
                    try:
                        result = await function_handlers[func_name](tool_call.function.arguments)
                        self.update_function_call_count(func_name)
                        results.append(result)
                    except Exception as e:
                        results.append({"error": str(e)})

        return results

    async def analyze_company_metrics(self, company: str, metric_type: str) -> List[Dict]:
        """Analyze company metrics using available search APIs."""
        query = f"Analyze {metric_type} metrics for {company}"
        messages = [{"role": "user", "content": query}]
        
        try:
            results = await self.send_query_with_functions(messages, query)
            
            # If we got search results, process them
            if isinstance(results, list) and len(results) > 0:
                # Extract relevant information from search results
                processed_results = []
                for result in results:
                    processed_result = {
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": result.get("content", ""),
                        "source": "Tavily Search",
                        "score": result.get("score", 0)
                    }
                    processed_results.append(processed_result)
                
                # Sort results by relevance score
                processed_results.sort(key=lambda x: x["score"], reverse=True)
                return processed_results
            
            return []
        except Exception as e:
            print(f"Error analyzing company metrics: {str(e)}")
            return []

    def write_analysis_to_file(self, research_results: List[Dict], filename_prefix: str) -> str:
        """Write research results to a markdown file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.md"
        
        with open(filename, 'w') as f:
            for result in research_results:
                # Write title
                f.write(f"# {result['title']}\n\n")
                
                # Write source and timestamp
                f.write(f"**Source:** {result['source']}\n")
                f.write(f"**Generated:** {result['timestamp']}\n\n")
                
                # Write sections if present
                if 'sections' in result:
                    for section in result['sections']:
                        f.write(f"## {section['title']}\n\n")
                        f.write(f"{section['content']}\n\n")
                else:
                    # Write content directly if no sections
                    f.write(result.get('content', ''))
                
                # Write URL if present
                if 'url' in result:
                    f.write(f"\nSource URL: {result['url']}\n")
                
                f.write("\n---\n\n")
        
        return filename

    async def lookup_api_docs(self, api_name: str = None, category: str = None) -> Dict[str, Any]:
        """Look up API documentation from data_resources_and_apis.md.
        
        Args:
            api_name: Optional name of the API to look up
            category: Optional category to filter by
            
        Returns:
            Dict containing the found documentation
        """
        try:
            # Read the markdown file
            with open("/Users/srvo/local/data_resources_and_apis.md", 'r') as f:
                content = f.read()
            
            # Split into sections based on headers
            sections = {}
            current_section = None
            current_content = []
            
            for line in content.split('\n'):
                if line.startswith('##'):
                    if current_section:
                        sections[current_section] = '\n'.join(current_content)
                    current_section = line.strip('# ')
                    current_content = []
                else:
                    current_content.append(line)
            
            # Add the last section
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            
            # If looking for a specific API
            if api_name:
                api_info = {}
                # Search in Active API Keys section
                active_apis = sections.get('Active API Keys and Configurations', '')
                if api_name.lower() in active_apis.lower():
                    # Parse the markdown table
                    for line in active_apis.split('\n'):
                        if '|' in line and api_name.lower() in line.lower():
                            parts = [p.strip() for p in line.split('|')]
                            if len(parts) >= 5:
                                api_info['status'] = parts[2]
                                api_info['key_location'] = parts[3]
                                api_info['notes'] = parts[4]
                
                # Search in other sections for more details
                for section, content in sections.items():
                    if api_name.lower() in content.lower():
                        # Parse tables in the section
                        table_data = []
                        in_table = False
                        headers = []
                        
                        for line in content.split('\n'):
                            if '|' in line:
                                if not in_table:
                                    # This is the header row
                                    headers = [h.strip() for h in line.split('|')[1:-1]]
                                    in_table = True
                                elif not line.strip().startswith('|-'):
                                    # This is a data row
                                    data = [d.strip() for d in line.split('|')[1:-1]]
                                    if len(data) == len(headers):
                                        row_dict = dict(zip(headers, data))
                                        if api_name.lower() in str(row_dict).lower():
                                            table_data.append(row_dict)
                        
                        if table_data:
                            api_info['details'] = table_data
                            api_info['category'] = section
                
                return api_info
            
            # If looking for a category
            elif category:
                for section, content in sections.items():
                    if category.lower() in section.lower():
                        return {
                            'category': section,
                            'content': content
                        }
            
            # If no specific search, return all sections
            return sections
            
        except Exception as e:
            print(f"Error looking up API docs: {str(e)}")
            print(f"Stack trace:\n{format_exc()}")
            return {}

    async def handle_api_error(self, error: Exception, function_name: str, query: str) -> None:
        """Handle API errors by fetching documentation if available."""
        # First try to find documentation in data_resources_and_apis.md
        api_docs = await self.lookup_api_docs(api_name=function_name)
        docs_found = False
        
        if api_docs:
            docs_found = True
            print(f"\nFound documentation for {function_name} in local resources:")
            if 'status' in api_docs:
                print(f"Status: {api_docs['status']}")
                print(f"Key Location: {api_docs['key_location']}")
                print(f"Notes: {api_docs['notes']}")
            if 'details' in api_docs:
                print("\nAdditional Details:")
                for detail in api_docs['details']:
                    for key, value in detail.items():
                        print(f"{key}: {value}")
            print("\n")

        # Then try to fetch online documentation if available
        function = next((f for f in self.functions if f["function"]["name"] == function_name), None)
        if not function:
            print(f"No function definition found for {function_name}")
            return

        api_docs_url = function["function"]["metadata"].get("api_docs_url")
        if api_docs_url:
            online_docs = await self.fetch_api_docs(api_docs_url)
            if online_docs:
                docs_found = True
                print(f"Found online documentation for {function_name}")
        
        if not docs_found:
            print(f"No documentation found for {function_name}")
            return

        # Combine local and online documentation for analysis
        docs = f"""
Local Documentation:
{json.dumps(api_docs, indent=2)}

Online Documentation:
{online_docs if 'online_docs' in locals() else 'Not available'}
"""

        # Ask DeepSeek for help with the error
        messages = [
            {"role": "system", "content": "You are a helpful assistant that helps fix API integration issues."},
            {"role": "user", "content": f"""
Tool: {function_name}
Error: {str(error)}
Error Type: {type(error).__name__}
Query: {query}

Documentation:
{docs}

Please analyze:
1. What caused this error with the {function_name} tool?
2. How can I fix it?
3. Are there any specific requirements or limitations in the documentation that I should be aware of?
"""}
        ]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": "deepseek-chat",
                        "messages": messages
                    }
                )
                response.raise_for_status()
                data = response.json()
                suggestion = data["choices"][0]["message"]["content"]
                print(f"\n=== API Error Analysis for {function_name} ===")
                print(f"Tool: {function_name}")
                print(f"Error Type: {type(error).__name__}")
                print(f"Error Message: {str(error)}")
                print(f"\nAnalysis and Suggestions:")
                print(f"{suggestion}\n")
                print("=" * 50 + "\n")
        except Exception as e:
            print(f"Error getting API error analysis for {function_name}: {str(e)}")
            print(f"Original error: {str(error)}")

    async def conduct_research(self, initial_query: str, follow_up_questions: List[str], 
                               context: Optional[Dict] = None) -> List[Dict]:
        """Conduct a multi-step research process with follow-up questions."""
        research_results = []
        messages = [
            {"role": "system", "content": "You are a helpful research assistant."}
        ]
        
        if context:
            messages.append({"role": "system", "content": json.dumps(context)})
        
        # Initial research
        messages.append({"role": "user", "content": initial_query})
        initial_response = await self.send_query_with_functions(
            messages=messages,
            query=initial_query
        )
        
        if initial_response:
            research_results.append({
                "title": "Initial Research",
                "content": initial_response.get("content", ""),
                "source": initial_response.get("source", "DeepSeek Research"),
                "timestamp": datetime.now().isoformat()
            })
        
        # Follow-up questions
        for question in follow_up_questions:
            messages.extend([
                {"role": "assistant", "content": research_results[-1]["content"]},
                {"role": "user", "content": question}
            ])
            
            follow_up_response = await self.send_query_with_functions(
                messages=messages,
                query=question
            )
            
            if follow_up_response:
                research_results.append({
                    "title": f"Follow-up Research: {question[:50]}...",
                    "content": follow_up_response.get("content", ""),
                    "source": follow_up_response.get("source", "DeepSeek Research"),
                    "timestamp": datetime.now().isoformat()
                })
        
        return research_results

    async def research_with_docs(self, query: str, api_name: str, 
                               follow_up_questions: List[str]) -> List[Dict]:
        """Conduct research with API documentation context."""
        # Get API documentation
        api_docs = await self.lookup_api_docs(api_name=api_name)
        if not api_docs:
            print(f"No documentation found for {api_name}")
            return []
        
        # Create documentation context
        doc_context = {
            "API Documentation": {
                "Name": api_name,
                "Status": api_docs.get("status", "Unknown"),
                "Key Location": api_docs.get("key_location", "Unknown"),
                "Notes": api_docs.get("notes", "")
            }
        }
        
        # Add documentation overview to results
        research_results = [{
            "title": f"{api_name} Documentation Overview",
            "content": json.dumps(doc_context, indent=2),
            "source": "Local Documentation",
            "timestamp": datetime.now().isoformat()
        }]
        
        # Conduct research with documentation context
        additional_results = await self.conduct_research(
            initial_query=query,
            follow_up_questions=follow_up_questions,
            context=doc_context
        )
        
        research_results.extend(additional_results)
        return research_results

    def format_research_results(self, results: List[Dict], title: str) -> List[Dict]:
        """Format research results into a structured report."""
        if not results:
            return []
        
        sections = []
        for i, result in enumerate(results):
            section_title = result.get("title", f"Research Step {i+1}")
            sections.append({
                "title": section_title,
                "content": result.get("content", "")
            })
        
        return [{
            "title": title,
            "sections": sections,
            "source": "DeepSeek Research",
            "timestamp": datetime.now().isoformat()
        }]

# Example usage:
"""
# Initialize the helper
helper = DeepSeekFunctionHelper(api_key="your-api-key")

# Define functions
api_list = [
    {
        "name": "get_weather",
        "description": "Get weather of a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city and state"
                }
            },
            "required": ["location"]
        },
        "metadata": {
            "keywords": ["weather", "temperature", "forecast"],
            "rate_limit": 100,
            "priority": 1
        }
    }
]

helper.define_api_functions(api_list)

# Define function handlers
async def weather_handler(args):
    # Implement actual weather API call
    return {"temperature": 20, "condition": "sunny"}

function_handlers = {
    "get_weather": weather_handler
}

# Use the helper
messages = [{"role": "user", "content": "What's the weather in San Francisco?"}]
results = await helper.handle_multiple_functions(
    "What's the weather in San Francisco?",
    messages,
    function_handlers
)
""" 