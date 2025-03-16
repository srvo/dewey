from __future__ import annotations

import asyncio
import json
import os
from typing import TYPE_CHECKING

import logfire
from backend.agent_search import stream_pro_search_qa
from backend.chat import stream_qa_objects
from backend.db.chat import get_chat_history, get_thread
from backend.db.engine import get_session
from backend.schemas import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponseEvent,
    ErrorStream,
    StreamEvent,
    ThreadResponse,
)
from backend.utils import strtobool
from backend.validators import validate_model
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_ipaddr
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from sqlalchemy.orm import Session

load_dotenv()


def create_error_event(detail: str) -> ServerSentEvent:
    """Creates an error event for streaming.

    Args:
        detail: The error message.

    Returns:
        A ServerSentEvent containing the error message.

    """
    obj = ChatResponseEvent(
        data=ErrorStream(detail=detail),
        event=StreamEvent.ERROR,
    )
    return ServerSentEvent(
        data=json.dumps(jsonable_encoder(obj)),
        event=StreamEvent.ERROR,
    )


def configure_logging(app: FastAPI, logfire_token: str | None) -> None:
    """Configures logging for the FastAPI app using Logfire.

    Args:
        app: The FastAPI application instance.
        logfire_token: The Logfire API token. If None, logging is disabled.

    """
    if logfire_token:
        logfire.configure()
        logfire.instrument_fastapi(app)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handles rate limit exceeded exceptions.

    Args:
        request: The request that triggered the exception.
        exc: The RateLimitExceeded exception.

    Returns:
        An EventSourceResponse containing an error message.

    """

    async def generator() -> AsyncGenerator[str, None]:
        yield json.dumps(
            jsonable_encoder(
                create_error_event("Rate limit exceeded, please try again later."),
            ),
        )

    return EventSourceResponse(
        generator(),
        media_type="text/event-stream",
    )


def configure_rate_limiting(
    app: FastAPI,
    rate_limit_enabled: str,
    redis_url: str | None,
) -> None:
    """Configures rate limiting for the FastAPI app.

    Args:
        app: The FastAPI application instance.
        rate_limit_enabled: Whether rate limiting is enabled (string representation of a boolean).
        redis_url: The URL of the Redis server for rate limiting.

    """
    limiter = Limiter(
        key_func=get_ipaddr,
        enabled=strtobool(rate_limit_enabled) and redis_url is not None,
        storage_uri=redis_url,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore


def configure_middleware(app: FastAPI) -> None:
    """Configures middleware for the FastAPI app.

    Args:
        app: The FastAPI application instance.

    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://research.sloane-collective.com",
            "http://research.sloane-collective.com",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def create_app() -> FastAPI:
    """Creates and configures the FastAPI app.

    Returns:
        A FastAPI application instance.

    """
    app = FastAPI()
    configure_middleware(app)
    configure_logging(app, os.getenv("LOGFIRE_TOKEN"))
    configure_rate_limiting(
        app,
        os.getenv("RATE_LIMIT_ENABLED", "false"),
        os.getenv("REDIS_URL"),
    )
    return app


app = create_app()


async def chat_stream_generator(
    chat_request: ChatRequest,
    request: Request,
    session: Session,
) -> AsyncGenerator[str, None]:
    """Generates a stream of chat response events.

    Args:
        chat_request: The chat request.
        request: The FastAPI request object.
        session: The database session.

    Yields:
        JSON strings representing ChatResponseEvent objects.

    """
    try:
        validate_model(chat_request.model)
        stream_fn = (
            stream_pro_search_qa if chat_request.pro_search else stream_qa_objects
        )
        async for obj in stream_fn(request=chat_request, session=session):
            if await request.is_disconnected():
                break
            yield json.dumps(jsonable_encoder(obj))
            await asyncio.sleep(0)
    except Exception as e:
        yield json.dumps(jsonable_encoder(create_error_event(str(e))))
        await asyncio.sleep(0)


@app.post("/chat")
@app.state.limiter.limit("4/min")
async def chat(
    chat_request: ChatRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> EventSourceResponse:
    """Chat endpoint that streams responses.

    Args:
        chat_request: The chat request.
        request: The FastAPI request object.
        session: The database session.

    Returns:
        An EventSourceResponse containing the chat stream.

    """
    return EventSourceResponse(chat_stream_generator(chat_request, request, session), media_type="text/event-stream")  # type: ignore


@app.get("/history")
async def recents(session: Session = Depends(get_session)) -> ChatHistoryResponse:
    """Retrieves recent chat history.

    Args:
        session: The database session.

    Returns:
        A ChatHistoryResponse object containing the chat history.

    Raises:
        HTTPException: If the database is disabled or an error occurs.

    """
    db_enabled = strtobool(os.environ.get("DB_ENABLED", "true"))
    if db_enabled:
        try:
            history = get_chat_history(session=session)
            return ChatHistoryResponse(snapshots=history)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(
            status_code=400,
            detail="Chat history is not available when DB is disabled. Please try self-hosting the app by following the instructions here: https://github.com/rashadphz/farfalle",
        )


@app.get("/thread/{thread_id}")
async def thread(
    thread_id: int,
    session: Session = Depends(get_session),
) -> ThreadResponse:
    """Retrieves a specific chat thread.

    Args:
        thread_id: The ID of the thread to retrieve.
        session: The database session.

    Returns:
        A ThreadResponse object containing the chat thread.

    """
    return get_thread(session=session, thread_id=thread_id)
