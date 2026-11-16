"""Read-only FastAPI service over the ingestion snapshot."""

from typing import Annotated
import os

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from .search import SearchParams, filter_jobs, rank_jobs
from .store import StoreUnavailable, load_snapshot
from .semantic import SemanticUnavailable, recommend_semantic
from .agent import AgentRequest, AgentUnavailable, InvalidToolCall, interpret_query

app = FastAPI(title="JobCompass", version="0.2.0", description="Real jobs, explicit constraints, explainable recommendations.")


@app.exception_handler(AgentUnavailable)
async def agent_unavailable(request, error):
    return JSONResponse(status_code=503, content={"detail": str(error), "code": "llm_unavailable"})


@app.exception_handler(InvalidToolCall)
async def invalid_tool_call(request, error):
    return JSONResponse(status_code=502, content={"detail": str(error), "code": "invalid_tool_call"})


@app.exception_handler(SemanticUnavailable)
async def semantic_unavailable(request, error):
    return JSONResponse(status_code=503, content={"detail": str(error), "code": "semantic_unavailable"})


@app.exception_handler(StoreUnavailable)
async def unavailable(request, error):
    return JSONResponse(status_code=503, content={"detail": str(error), "code": "data_unavailable"})


@app.get("/health")
def health():
    storage = "postgresql" if os.environ.get("DATABASE_URL") else "json"
    try:
        snapshot = load_snapshot()
        return {"status": "ok", "ready": True, "storage": storage, "stored_jobs": len(snapshot["records"])}
    except StoreUnavailable as error:
        return {"status": "ok", "ready": False, "storage": storage, "detail": str(error)}


def result_page(snapshot, params, recommendations=False):
    records = filter_jobs(snapshot["records"], params, keyword_mode="any" if recommendations else "all")
    ranked = rank_jobs(records, params.q)
    return serialize_page(snapshot, params, ranked)


def serialize_page(snapshot, params, ranked, mode="deterministic"):
    items = []
    for row in ranked[params.offset:params.offset + params.limit]:
        # Serve normalized evidence; avoid shipping full raw HTML/provider payloads.
        items.append({key: value for key, value in row.items() if key not in {"raw_payload", "description_html"}})
    return {
        "items": items, "total": len(ranked), "limit": params.limit, "offset": params.offset, "mode": mode,
        "attribution": snapshot["attribution"], "feed_fetched_at": snapshot["feed_fetched_at"],
        "feed_complete": snapshot["feed_complete"],
        "rules": {"country": "Unknown eligibility is excluded when country is requested; timezone rules are returned, not inferred.",
                  "salary": "Reported minimum must meet the requested floor in the same currency and pay period.",
                  "score": "70 * positive cosine similarity + 0.3 * lexical score" if mode == "hybrid" else "60 title + 30 description + 10 categories, scaled by matched query terms."},
    }


@app.get("/jobs")
def jobs(params: Annotated[SearchParams, Query()], snapshot: dict = Depends(load_snapshot)):
    return result_page(snapshot, params)


@app.get("/recommendations")
def recommendations(params: Annotated[SearchParams, Query()], snapshot: dict = Depends(load_snapshot)):
    return result_page(snapshot, params, recommendations=True)


@app.get("/search")
def semantic_search(params: Annotated[SearchParams, Query()], snapshot: dict = Depends(load_snapshot)):
    if not params.q:
        raise HTTPException(422, "Semantic search requires q")
    return serialize_page(snapshot, params, recommend_semantic(snapshot["records"], params), mode="hybrid")


@app.post("/agent/query")
def agent_query(request: AgentRequest):
    params = interpret_query(request)
    snapshot = load_snapshot()
    if request.mode == "hybrid":
        results = serialize_page(snapshot, params, recommend_semantic(snapshot["records"], params), mode="hybrid")
    else:
        results = result_page(snapshot, params, recommendations=True)
    return {"interpreted_query": params.model_dump(mode="json"), "tool": "search_jobs", "results": results}
