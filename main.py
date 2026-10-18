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
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver      
from pydantic import BaseModel, Field, field_validator

from graph import build

logger = logging.getLogger("verriffy")




        


fastapi_app = FastAPI(
    title="Verriffy API",
    description="AI-assisted insurance claim analysis: chat with the assistant, ask for a claim analysis, "
                "get a review score with reasons and evidence for a human reviewer.",
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





async def _invoke(query_text: str, thread_id: str,) 
               async with         AsyncPostgresSaver.from_conn_string(config.DATABASE_URL) as cp:
            await cp.setup()
            app = build.compile(checkpointer=cp)
           result = await app.ainvoke(
    {"messages": [HumanMessage(content=query_text)]},
    config={
        "configurable": {
            "thread_id": thread_id
        }
    }

)
          return result 
            
             
            
    else:
        logger.warning("DATABASE_URL is not set: chat memory is kept in RAM and is lost on restart")
    
    


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

async def claim_agent(request: str , thread_id : str ):
    
    try:
        result = await _invoke(request,thread_id )
        return {"reply":
_text_of(result["messages"][-1].content)
              } 

    except Exception:
        logger.exception("[claim_agent] server-side error")
        raise HTTPException(status_code=500, detail="Internal error occurred, please try again later")
