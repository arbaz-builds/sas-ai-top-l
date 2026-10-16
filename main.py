
"""FastAPI app — exposes the blog-writing graph over HTTP, with Postgres-backed memory."""
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from graph import build 
import config

config.validate()

fastapi_app = FastAPI(
    title="",
    description="",
    version="1.0.0",
    contact={"name": "Mohammad Arbaz", "url": "https://github.com/arbaz-builds"},
)



@fastapi_app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    messages = [err["msg"] for err in errors]
    return JSONResponse(
        status_code=400,
        content={"error": "Bad Request", "message": "; ".join(messages)}
    )


async def _invoke(query_text: str, thread_id: str = "1") -> dict:
    """
    """
    async with AsyncPostgresSaver.from_conn_string(config.DATABASE_URL) as cp:
        await cp.setup()
        result = await build.compile(checkpointer=cp).ainvoke(
            {"memory": [HumanMessage(content=query_text)]},
            config={"configurable": {"thread_id": thread_id}},
        )
    return result

@fastapi_app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "idea-api"
    }


@fastapi_app.post(
    "/Agent",
    summary="",
    description="",
    response_description="",
    tags=[""],
)
async def BlogAgent(request: QueryRequest):
    try:
        result = await _invoke(request.query_text, request.thread_id)
        
        return {"messages": result}
            
    except Exception as e:
        print(f"[BlogAgent] Server-side error: {e}")
        raise HTTPException(status_code=500, detail="Internal error occurred, please try again later")