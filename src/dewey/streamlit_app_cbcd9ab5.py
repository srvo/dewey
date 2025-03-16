import os

import requests
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Configure API clients
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1",
)

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searx.rawls.cursor.sh")


def search(query, num_results=5):
    """Search using local SearxNG instance."""
    response = requests.get(
        f"{SEARXNG_URL}/search",
        params={
            "q": query,
            "format": "json",
            "engines": "google",
            "language": "en",
            "time_range": "",
            "safesearch": 1,
            "categories": "general",
        },
    )
    results = response.json()
    return results.get("results", [])[:num_results]


def get_completion(prompt, context=""):
    """Get completion from DeepSeek API."""
    messages = []
    if context:
        messages.append({"role": "system", "content": context})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0.7,
        max_tokens=1000,
    )
    return response.choices[0].message.content


# Streamlit UI
st.title("STORM Demo")

# Input section
query = st.text_input("Enter your query:")

if query:
    with st.spinner("Searching..."):
        # Get search results
        results = search(query)

        # Format context from search results
        context = "\n\n".join(
            [
                f"Title: {r.get('title', '')}\nURL: {r.get('url', '')}\nSnippet: {r.get('content', '')}"
                for r in results
            ],
        )

        # Generate response using DeepSeek
        system_prompt = f"""You are a helpful AI assistant. Use the following search results to help answer the user's question:

{context}

Base your response on the search results above. If you cannot find relevant information in the results, say so."""

        response = get_completion(query, system_prompt)

        # Display results
        st.subheader("Search Results")
        for r in results:
            st.markdown(f"**[{r.get('title', '')}]({r.get('url', '')})**")
            st.write(r.get("content", ""))
            st.markdown("---")

        st.subheader("AI Response")
        st.write(response)
