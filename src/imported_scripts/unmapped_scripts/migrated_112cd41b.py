import asyncio
from collections.abc import AsyncIterator

from backend.constants import get_model_string
from backend.db.chat import save_turn_to_db
from backend.llm.base import BaseLLM, EveryLLM
from backend.prompts import CHAT_PROMPT, HISTORY_QUERY_REPHRASE
from backend.related_queries import generate_related_queries
from backend.schemas import (
    BeginStream,
    ChatRequest,
    ChatResponseEvent,
    FinalResponseStream,
    Message,
    RelatedQueriesStream,
    SearchResult,
    SearchResultStream,
    StreamEndStream,
    StreamEvent,
    TextChunkStream,
)
from backend.search.search_service import perform_search
from backend.utils import is_local_model
from fastapi import HTTPException
from sqlalchemy.orm import Session


def rephrase_query_with_history(
    question: str,
    history: list[Message],
    llm: BaseLLM,
) -> str:
    """Rephrases the query based on the chat history.

    Args:
        question: The user's current question.
        history: A list of previous messages in the chat.
        llm: The language model to use for rephrasing.

    Returns:
        The rephrased query.

    Raises:
        HTTPException: If the model is at capacity.

    """
    if not history:
        return question

    try:
        history_str = "\n".join(f"{msg.role}: {msg.content}" for msg in history)
        formatted_query = HISTORY_QUERY_REPHRASE.format(
            chat_history=history_str,
            question=question,
        )
        return llm.complete(formatted_query).text.replace('"', "")
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Model is at capacity. Please try again later.",
        )


def format_context(search_results: list[SearchResult]) -> str:
    """Formats the search results into a context string.

    Args:
        search_results: A list of search results.

    Returns:
        A string containing the formatted search results.

    """
    return "\n\n".join(
        [f"Citation {i+1}. {result!s}" for i, result in enumerate(search_results)],
    )


async def generate_llm_response_stream(
    query: str,
    search_results: list[SearchResult],
    llm: BaseLLM,
) -> AsyncIterator[ChatResponseEvent]:
    """Generates a stream of text chunks from the language model.

    Args:
        query: The user's query.
        search_results: A list of search results.
        llm: The language model to use for generating the response.

    Yields:
        ChatResponseEvent: Events containing text chunks from the LLM.

    """
    fmt_qa_prompt = CHAT_PROMPT.format(
        my_context=format_context(search_results),
        my_query=query,
    )

    full_response = ""
    response_gen = await llm.astream(fmt_qa_prompt)
    async for completion in response_gen:
        delta = completion.delta or ""
        full_response += delta
        yield ChatResponseEvent(
            event=StreamEvent.TEXT_CHUNK,
            data=TextChunkStream(text=delta),
        )
    yield full_response


async def stream_qa_objects(
    request: ChatRequest,
    session: Session,
) -> AsyncIterator[ChatResponseEvent]:
    """Streams question answering objects.

    Args:
        request: The chat request.
        session: The database session.

    Yields:
        ChatResponseEvent: Events representing the different stages of the
            question answering process.

    Raises:
        HTTPException: If an error occurs during the process.

    """
    try:
        model_name = get_model_string(request.model)
        llm = EveryLLM(model=model_name)

        yield ChatResponseEvent(
            event=StreamEvent.BEGIN_STREAM,
            data=BeginStream(query=request.query),
        )

        query = rephrase_query_with_history(request.query, request.history, llm)

        search_response = await perform_search(query)

        search_results = search_response.results
        images = search_response.images

        # Only create the task first if the model is not local
        related_queries_task = None
        if not is_local_model(request.model):
            related_queries_task = asyncio.create_task(
                generate_related_queries(query, search_results, llm),
            )

        yield ChatResponseEvent(
            event=StreamEvent.SEARCH_RESULTS,
            data=SearchResultStream(
                results=search_results,
                images=images,
            ),
        )

        full_response = await generate_llm_response_stream(
            query,
            search_results,
            llm,
        ).__anext__()

        related_queries = await (
            related_queries_task
            if related_queries_task
            else generate_related_queries(query, search_results, llm)
        )

        yield ChatResponseEvent(
            event=StreamEvent.RELATED_QUERIES,
            data=RelatedQueriesStream(related_queries=related_queries),
        )

        thread_id = save_turn_to_db(
            session=session,
            thread_id=request.thread_id,
            user_message=request.query,
            assistant_message=full_response,
            model=request.model,
            search_results=search_results,
            image_results=images,
            related_queries=related_queries,
        )

        yield ChatResponseEvent(
            event=StreamEvent.FINAL_RESPONSE,
            data=FinalResponseStream(message=full_response),
        )

        yield ChatResponseEvent(
            event=StreamEvent.STREAM_END,
            data=StreamEndStream(thread_id=thread_id),
        )

    except Exception as e:
        detail = str(e)
        raise HTTPException(status_code=500, detail=detail)
