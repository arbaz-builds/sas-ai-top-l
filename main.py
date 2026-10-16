"""Verriffy API: exposes the claim-analysis graph over HTTP, with chat memory per thread
(Postgres when DATABASE_URL is set, otherwise RAM for local development).

Run:  uvicorn main:fastapi_app --reload
"""
import logging
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional

import config

config.validate()  # fail early, with a clear message, if a key is missing (before the models are created)

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field, field_validator

from graph import build

logger = logging.getLogger("verriffy")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # the memory connection and the compiled graph are created ONCE, not on every request
    if config.DATABASE_URL:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        async with AsyncPostgresSaver.from_conn_string(config.DATABASE_URL) as cp:
            await cp.setup()
            app.state.graph = build.compile(checkpointer=cp)
            yield
    else:
        logger.warning("DATABASE_URL is not set: chat memory is kept in RAM and is lost on restart")
        app.state.graph = build.compile(checkpointer=MemorySaver())
        yield


fastapi_app = FastAPI(
    title="Verriffy API",
    description="AI-assisted insurance claim analysis: chat with the assistant, ask for a claim analysis, "
                "get a review score with reasons and evidence for a human reviewer.",
    version="1.0.0",
    contact={"name": "Mohammad Arbaz", "url": "https://github.com/arbaz-builds"},
    lifespan=lifespan,
)


@fastapi_app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    messages = [err["msg"] for err in errors]
    return JSONResponse(
        status_code=400,
        content={"error": "Bad Request", "message": "; ".join(messages)}
    )


class QueryRequest(BaseModel):
    query_text: str = Field(min_length=1, description="The user's message")
    thread_id: Optional[str] = Field(
        default=None,
        description="Conversation id. Send the same id to continue a conversation; leave empty to start a new one.",
    )
    images: List[str] = Field(
        default_factory=list,
        max_length=6,
        description="Optional images sent with the message, as data URLs (data:image/jpeg;base64,...)",
    )

    @field_validator("images")
    @classmethod
    def _images_are_data_urls(cls, v):
        if any(not s.startswith("data:image/") for s in v):
            raise ValueError("images must be data URLs that start with 'data:image/'")
        return v


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    return "\n".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")


async def _invoke(query_text: str, thread_id: str, images: List[str]) -> dict:
    if images:
        content = [{"type": "text", "text": query_text}] + [{"type": "image_url", "image_url": {"url": u}} for u in images]
    else:
        content = query_text

    return await fastapi_app.state.graph.ainvoke(
        {
            "messages": [HumanMessage(content=content)],
            # reset the analysis fields every turn, so an old result is never shown for a new message
            "TextDATA": "", "ImageDATA": "", "Dataprocess": "", "Finaloutput": "",
        },
        config={"configurable": {"thread_id": thread_id}},
    )


@fastapi_app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "verriffy-api"
    }


@fastapi_app.post(
    "/chat",
    summary="Chat with the Verriffy assistant",
    description="Normal chat gets a normal reply. When the user clearly asks for a claim analysis and gives enough "
                "details, the analysis runs and `final_output` holds the score, reasons and evidence.",
    response_description="The assistant's reply, and the analysis result when an analysis ran",
    tags=["chat"],
)
async def claim_agent(request: QueryRequest):
    thread_id = request.thread_id or str(uuid.uuid4())
    try:
        result = await _invoke(request.query_text, thread_id, request.images)
        return {
            "thread_id": thread_id,
            "reply": _text_of(result["messages"][-1].content),
            "final_output": result.get("Finaloutput") or None,
        }

    except Exception:
        logger.exception("[claim_agent] server-side error")
        raise HTTPException(status_code=500, detail="Internal error occurred, please try again later")
