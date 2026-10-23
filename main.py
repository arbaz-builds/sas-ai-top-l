"""
Verriffy API:
Exposes the claim-analysis graph over HTTP, with chat memory per thread.

PostgreSQL is used when DATABASE_URL is configured.
Otherwise, in-memory execution is used for local development.

Run:
    uvicorn main:fastapi_app --reload
"""

import logging
import uuid

from contextlib import asynccontextmanager

import config

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from pydantic import BaseModel, Field, field_validator

from graph import build


logger = logging.getLogger("verriffy")


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class ChatRequest(BaseModel):
    request: str = Field(
        ...,
        min_length=1,
        description="Message sent by the user",
    )

    thread_id: str = Field(
        ...,
        min_length=1,
        description="Conversation ID returned by /new-chat",
    )

    @field_validator("request", "thread_id")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Field cannot be empty")

        return value


# --------------------------------------------------
# APPLICATION LIFESPAN
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Verriffy API starting")

    yield

    logger.info("Verriffy API shutting down")


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

fastapi_app = FastAPI(
    title="Verriffy API",
    description=(
        "AI-assisted insurance claim analysis. "
        "Chat with the assistant, request claim analysis, "
        "and receive review scores, reasons and evidence."
    ),
    version="1.0.0",
    contact={
        "name": "Mohammad Arbaz",
        "url": "https://github.com/arbaz-builds",
    },
    lifespan=lifespan,
)


# --------------------------------------------------
# CORS MIDDLEWARE
# --------------------------------------------------

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# VALIDATION ERROR HANDLER
# --------------------------------------------------

@fastapi_app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    errors = exc.errors()
    messages = [error["msg"] for error in errors]

    return JSONResponse(
        status_code=400,
        content={
            "error": "Bad Request",
            "message": "; ".join(messages),
        },
    )


# --------------------------------------------------
# GRAPH INVOCATION
# --------------------------------------------------

async def _invoke(query_text: str, thread_id: str):
    """
    Invoke the LangGraph application using the supplied
    thread ID so messages in the same thread share state.
    """

    graph_app = None

    if config.DATABASE_URL:
        async with AsyncPostgresSaver.from_conn_string(
            config.DATABASE_URL
        ) as checkpointer:

            await checkpointer.setup()

            graph_app = build.compile(
                checkpointer=checkpointer
            )

            result = await graph_app.ainvoke(
                {
                    "messages": [
                        HumanMessage(content=query_text)
                    ]
                },
                config={
                    "configurable": {
                        "thread_id": thread_id
                    }
                },
            )

            return result

    logger.warning(
        "DATABASE_URL is not set: "
        "using in-memory execution without persistent checkpoints"
    )

    graph_app = build.compile()

    result = await graph_app.ainvoke(
        {
            "messages": [
                HumanMessage(content=query_text)
            ]
        },
        config={
            "configurable": {
                "thread_id": thread_id
            }
        },
    )

    return result


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@fastapi_app.get(
    "/health",
    tags=["system"],
)
async def health_check():
    return {
        "status": "healthy",
        "service": "verriffy-api",
    }


# --------------------------------------------------
# CREATE NEW CHAT
# --------------------------------------------------

@fastapi_app.post(
    "/new-chat",
    summary="Create a new conversation",
    tags=["chat"],
)
async def new_chat():
    """
    Generate a new conversation ID.

    The frontend should call this endpoint only when
    the user explicitly starts a new chat.
    """

    thread_id = str(uuid.uuid4())

    return {
        "thread_id": thread_id,
        "message": "New chat created successfully",
    }


# --------------------------------------------------
# CHAT ENDPOINT
# --------------------------------------------------

@fastapi_app.post(
    "/chat",
    summary="Chat with the Verriffy assistant",
    description=(
        "Send a message using the thread ID returned "
        "by /new-chat. Reuse that ID for subsequent "
        "messages in the same conversation."
    ),
    tags=["chat"],
)
async def claim_agent(body: ChatRequest):

    try:
        result = await _invoke(
            query_text=body.request,
            thread_id=body.thread_id,
        )

        messages = result.get("messages", [])

        if not messages:
            raise HTTPException(
                status_code=500,
                detail="The assistant returned no messages",
            )

        return {
            "thread_id": body.thread_id,
            "reply": messages[-1].content,
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception(
            "[claim_agent] Server-side error"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Internal error occurred, "
                "please try again later"
            ),
        )