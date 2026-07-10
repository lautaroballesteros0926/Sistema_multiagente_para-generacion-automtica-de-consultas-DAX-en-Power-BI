from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from config.settings import settings
from mcp_server.powerbi.client import client
from orchestrator.graph import build_graph
from orchestrator.state import AgentState

router = APIRouter()


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    dax: str
    score: float
    decision: str
    iterations: int
    explanation: str
    syntax_valid: bool


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/schema")
async def get_schema() -> dict:
    schema = await client.fetch_schema()
    return schema.model_dump()


@router.post("/query", response_model=QueryResponse)
async def run_query(request: QueryRequest) -> QueryResponse:
    initial_state: AgentState = {
        "question": request.question,
        "dax_query": None,
        "evaluation": None,
        "iteration": 0,
        "max_iterations": settings.max_iterations,
        "final_result": None,
    }

    graph = build_graph()
    final_state = await graph.ainvoke(initial_state)
    final_result = final_state["final_result"]

    return QueryResponse(
        dax=final_result["dax"],
        score=final_result["score"],
        decision=final_result["decision"].value,
        iterations=final_result["iterations"],
        explanation=final_result["explanation"],
        syntax_valid=final_result["syntax_valid"],
    )
