import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from jobcompass.api import app
from jobcompass.normalize import normalize_job
from jobcompass.store import load_snapshot


@pytest.fixture
def client(tmp_path, monkeypatch, raw_job):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    now = datetime.now(timezone.utc)
    raw_job["expiryDate"] = int((now + timedelta(days=1)).timestamp())
    row = {**normalize_job(raw_job, now).to_record(), "is_active": True, "status": "open", "status_checked_at": now.isoformat()}
    snapshot = {"records": [row], "attribution": {"label": "Himalayas", "url": "https://himalayas.app"},
                "feed_fetched_at": now.isoformat(), "feed_complete": False}
    (tmp_path / "jobs.json").write_text(json.dumps(snapshot))
    monkeypatch.setenv("JOBCOMPASS_DATA_DIR", str(tmp_path))
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_endpoints_return_normalized_jobs_and_attribution(client):
    assert client.get("/health").json()["ready"]
    response = client.get("/recommendations", params={"q": "python", "country": "IN"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["attribution"]["url"] == "https://himalayas.app"
    job = data["items"][0]
    assert job["country_eligibility"] == "eligible" and job["score"] >= 60
    assert job["application_url"].endswith("?utm_source=api")
    assert "raw_payload" not in job and "description_html" not in job


def test_pagination_and_empty_matches(client):
    assert client.get("/jobs?offset=1&limit=1").json()["items"] == []
    assert client.get("/jobs?country=US").json()["total"] == 0
    assert client.get("/recommendations?q=unmatchedword").json()["items"] == []


@pytest.mark.parametrize("query", ["limit=0", "offset=-1", "country=Atlantis", "min_salary=10", "q=%20", "surprise=1"])
def test_invalid_query_has_422(client, query):
    response = client.get("/jobs?" + query)
    assert response.status_code == 422
    assert response.json()["detail"]


def test_missing_snapshot_returns_clear_503(client, monkeypatch, tmp_path):
    monkeypatch.setenv("JOBCOMPASS_DATA_DIR", str(tmp_path / "missing"))
    assert not client.get("/health").json()["ready"]
    response = client.get("/jobs")
    assert response.status_code == 503 and response.json()["code"] == "data_unavailable"


def test_stale_status_cannot_be_served_as_current(client, tmp_path):
    path = tmp_path / "jobs.json"
    snapshot = json.loads(path.read_text())
    snapshot["records"][0]["status_checked_at"] = (datetime.now(timezone.utc) - timedelta(minutes=11)).isoformat()
    path.write_text(json.dumps(snapshot))
    assert client.get("/jobs").status_code == 503


def test_semantic_missing_query_or_model_is_explicit(client, monkeypatch):
    from jobcompass import api
    from jobcompass.semantic import SemanticUnavailable
    assert client.get("/search").status_code == 422
    def unavailable(*args):
        raise SemanticUnavailable("Index not available")
    monkeypatch.setattr(api, "recommend_semantic", unavailable)
    response = client.get("/search?q=software")
    assert response.status_code == 503
    assert response.json()["code"] == "semantic_unavailable"
    assert client.get("/recommendations?q=python").status_code == 200


def test_all_unverified_is_not_disguised_as_empty_success(client, tmp_path):
    path = tmp_path / "jobs.json"
    snapshot = json.loads(path.read_text())
    snapshot["records"][0].update(is_active=False, status="unverified")
    snapshot["status_errors"] = [{"reason": "source timeout"}]
    path.write_text(json.dumps(snapshot))
    assert client.get("/jobs").status_code == 503


def test_partial_status_failure_remains_visible(client, tmp_path):
    path = tmp_path / "jobs.json"
    snapshot = json.loads(path.read_text())
    unknown = {**snapshot["records"][0], "source_id": "test-only-unknown", "is_active": False, "status": "unverified"}
    snapshot["records"].append(unknown)
    snapshot["status_errors"] = [{"source_id": unknown["source_id"], "reason": "source timeout"}]
    path.write_text(json.dumps(snapshot))
    response = client.get("/jobs")
    assert response.status_code == 200 and response.json()["total"] == 1
    assert response.json()["data_quality"]["status_errors"] == 1
