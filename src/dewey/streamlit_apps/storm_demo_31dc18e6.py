```python
import os
from typing import List, Dict, Any

import requests
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI


def load_api_client() -> OpenAI:
    """Loads and configures the OpenAI API client."""
    load_dotenv()
    return OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com/v1"
    )


def search_searxng(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
    """Searches using a local SearxNG instance.

    Args:
        query: The search query.
        num_results: The number of search results to return.

    Returns:
        A list of search results, where each result is a dictionary.
    """
    searxng_url = os.getenv("SEARXNG_URL", "http://searx.rawls.cursor.sh")
    response = requests.get(
        f"{searxng_url}/search",
        params={
            "q": query,
            "format": "json",
            "engines": "google",
            "language": "en",
            "time_range": "",
            "safesearch": 1,
            "categories": "general"
        }
    )
    results = response.json()
    return results.get("results", [])[:num_results]


def get_completion(prompt: str, context: str = "") -> str:
    """Gets a completion from the DeepSeek API.

    Args:
        prompt: The user prompt.
        context: The system context.

    Returns:
        The completion from the API.
    """
    client = load_api_client()
    messages = []
    if context:
        messages.append({"role": "system", "content": context})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0.7,
        max_tokens=1000
    )
    return response.choices[0].message.content


def format_search_results_context(results: List[Dict[str, Any]]) -> str:
    """Formats search results into a context string.

    Args:
        results: A list of search results.

    Returns:
        A formatted context string.
    """
    return "\n\n".join([
        f"Title: {r.get('title', '')}\nURL: {r.get('url', '')}\nSnippet: {r.get('content', '')}"
        for r in results
    ])


def main():
    """Main function to run the Streamlit application."""
    st.title("STORM Demo")

    query = st.text_input("Enter your query:")

    if query:
        with st.spinner("Searching..."):
            results = search_searxng(query)

            context = format_search_results_context(results)

            system_prompt = f"""You are a helpful AI assistant. Use the following search results to help answer the user's question:

{context}

Base your response on the search results above. If you cannot find relevant information in the results, say so."""

            response = get_completion(query, system_prompt)

            st.subheader("Search Results")
            for r in results:
                st.markdown(f"**[{r.get('title', '')}]({r.get('url', '')})**")
                st.write(r.get('content', ''))
                st.markdown("---")

            st.subheader("AI Response")
            st.write(response)


if __name__ == "__main__":
    main()
```
