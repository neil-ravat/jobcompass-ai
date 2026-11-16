"""Read-only FastAPI service over the ingestion snapshot."""

from typing import Annotated

from fastapi import Depends, FastAPI, Query
from fastapi.responses import JSONResponse

from .search import SearchParams, filter_jobs, rank_jobs
from .store import StoreUnavailable, load_snapshot

app = FastAPI(title="JobCompass", version="0.2.0", description="Real jobs, explicit constraints, explainable recommendations.")


@app.exception_handler(StoreUnavailable)
async def unavailable(request, error):
    return JSONResponse(status_code=503, content={"detail": str(error), "code": "data_unavailable"})


@app.get("/health")
def health():
    try:
        snapshot = load_snapshot()
        return {"status": "ok", "ready": True, "storage": "json", "stored_jobs": len(snapshot["records"])}
    except StoreUnavailable as error:
        return {"status": "ok", "ready": False, "storage": "json", "detail": str(error)}


def result_page(snapshot, params, recommendations=False):
    records = filter_jobs(snapshot["records"], params, keyword_mode="any" if recommendations else "all")
    ranked = rank_jobs(records, params.q)
    items = []
    for row in ranked[params.offset:params.offset + params.limit]:
        # Serve normalized evidence; avoid shipping full raw HTML/provider payloads.
        items.append({key: value for key, value in row.items() if key not in {"raw_payload", "description_html"}})
    return {
        "items": items, "total": len(ranked), "limit": params.limit, "offset": params.offset,
        "attribution": snapshot["attribution"], "feed_fetched_at": snapshot["feed_fetched_at"],
        "feed_complete": snapshot["feed_complete"],
        "rules": {"country": "Unknown eligibility is excluded when country is requested; timezone rules are returned, not inferred.",
                  "salary": "Reported minimum must meet the requested floor in the same currency and pay period.",
                  "score": "60 title + 30 description + 10 categories, scaled by matched query terms."},
    }


@app.get("/jobs")
def jobs(params: Annotated[SearchParams, Query()], snapshot: dict = Depends(load_snapshot)):
    return result_page(snapshot, params)


@app.get("/recommendations")
def recommendations(params: Annotated[SearchParams, Query()], snapshot: dict = Depends(load_snapshot)):
    return result_page(snapshot, params, recommendations=True)
