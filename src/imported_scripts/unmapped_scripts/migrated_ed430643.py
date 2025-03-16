from backend.llm.base import BaseLLM
from backend.prompts import RELATED_QUESTION_PROMPT
from backend.schemas import RelatedQueries, SearchResult


def _prepare_context(search_results: list[SearchResult]) -> str:
    """Prepares the context string from search results.

    Args:
        search_results: A list of SearchResult objects.

    Returns:
        A string containing the concatenated search results, truncated to 4000 characters.

    """
    context = "\n\n".join([f"{result!s}" for result in search_results])
    return context[:4000]


def _clean_queries(queries: list[str]) -> list[str]:
    """Cleans a list of queries by lowercasing and removing question marks.

    Args:
        queries: A list of query strings.

    Returns:
        A list of cleaned query strings.

    """
    return [query.lower().replace("?", "") for query in queries]


async def generate_related_queries(
    query: str,
    search_results: list[SearchResult],
    llm: BaseLLM,
) -> list[str]:
    """Generates related queries based on a given query and search results.

    Args:
        query: The original query string.
        search_results: A list of SearchResult objects.
        llm: An instance of a BaseLLM.

    Returns:
        A list of related query strings.

    """
    context = _prepare_context(search_results)
    related: RelatedQueries = await llm.structured_complete(
        RelatedQueries,
        RELATED_QUESTION_PROMPT.format(query=query, context=context),
    )

    return _clean_queries(related.related_questions)
