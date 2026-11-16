import json

import pytest
import requests

from jobcompass import semantic, worker
from jobcompass.himalayas import RetryDeferred
from jobcompass.normalize import normalize_job


def test_refresh_reuses_unchanged_embeddings(monkeypatch, tmp_path, raw_job, now):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    row = normalize_job(raw_job, now).to_record()
    snapshot = {"records": [row], "counts": {"stored": 1}, "feed_cache_used": True, "status_errors": [], "rejected_records": []}
    monkeypatch.setattr(worker, "ingest", lambda *args, **kwargs: snapshot)
    index = {"model": semantic.MODEL, "dimensions": 384, "rows": [{"source": row["source"], "source_id": row["source_id"],
        "content_hash": semantic.content_hash(row), "vector": [1.0]+[0.0]*383}]}
    (tmp_path / "embeddings.json").write_text(json.dumps(index))
    monkeypatch.setattr(semantic, "build_index", lambda *args: pytest.fail("Unchanged index should not regenerate"))
    result = worker.refresh_once(tmp_path, semantic=True)
    assert result["index"]["reused"] and result["feed_cache_used"]


def test_worker_honors_long_provider_cooldown():
    assert worker.retry_wait(RetryDeferred("wait", retry_after=3600), 300) == 3600
    response = requests.Response()
    response.status_code = 429
    response.headers["Retry-After"] = "7200"
    assert worker.retry_wait(requests.HTTPError(response=response), 300) == 7200
