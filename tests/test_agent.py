import json
import secrets
from unittest.mock import Mock

import pytest
import requests
from fastapi.testclient import TestClient

from jobcompass import agent, api
from jobcompass.search import SearchParams


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", secrets.token_urlsafe(24))  # Offline mock only.
    args = {"q": "python", "role": None, "country": "US", "remote_only": False,
            "min_salary": None, "currency": None, "salary_period": None, "limit": 10}
    payload = {"status": "completed", "output": [{"type": "function_call", "name": "search_jobs", "arguments": json.dumps(args)}]}
    response = Mock()
    response.json.return_value = payload
    post = Mock(return_value=response)
    monkeypatch.setattr(agent.requests, "post", post)
    return post, payload, args


def test_strict_schema_and_locked_constraints(provider):
    post, _, _ = provider
    params = agent.interpret_query(agent.AgentRequest(message="python roles", constraints=SearchParams(country="IN", remote_only=True)))
    assert params.country == "IN" and params.remote_only
    body = post.call_args.kwargs["json"]
    assert body["parallel_tool_calls"] is False and body["store"] is False
    schema = body["tools"][0]["parameters"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert body["tool_choice"]["name"] == "search_jobs"


def test_missing_key_makes_no_request(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    post = Mock()
    monkeypatch.setattr(agent.requests, "post", post)
    with pytest.raises(agent.AgentUnavailable, match="not configured"):
        agent.interpret_query(agent.AgentRequest(message="python roles"))
    post.assert_not_called()


@pytest.mark.parametrize("error", [requests.Timeout(), requests.HTTPError(), requests.ConnectionError()])
def test_provider_failure_is_safe(provider, error):
    post, _, _ = provider
    post.side_effect = error
    with pytest.raises(agent.AgentUnavailable):
        agent.interpret_query(agent.AgentRequest(message="python roles"))
    assert post.call_count == 1


@pytest.mark.parametrize("change", ["wrong_name", "no_call", "multiple_calls", "bad_json", "incomplete", "bad_output", "extra_field", "bad_country", "missing_field"])
def test_malformed_tool_calls_rejected(provider, change):
    _, payload, args = provider
    call = payload["output"][0]
    if change == "wrong_name": call["name"] = "run_sql"
    elif change == "no_call": payload["output"] = []
    elif change == "multiple_calls": payload["output"].append(call.copy())
    elif change == "bad_json": call["arguments"] = "not-json"
    elif change == "incomplete": payload["status"] = "incomplete"
    elif change == "bad_output": payload["output"] = [42]
    else:
        if change == "extra_field": args["sql"] = "DROP TABLE jobs"
        elif change == "bad_country": args["country"] = "Atlantis"
        elif change == "missing_field": del args["q"]
        call["arguments"] = json.dumps(args)
    with pytest.raises(agent.InvalidToolCall):
        agent.interpret_query(agent.AgentRequest(message="python roles"))


def test_agent_endpoint_missing_credentials_and_invalid_body(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with TestClient(api.app) as client:
        response = client.post("/agent/query", json={"message": "python roles"})
        assert response.status_code == 503 and response.json()["code"] == "llm_unavailable"
        assert client.post("/agent/query", json={"message": "  "}).status_code == 422


def test_agent_empty_retrieval_is_grounded(provider, monkeypatch, now):
    snapshot = {"records": [], "attribution": {"label": "Himalayas", "url": "https://himalayas.app"},
                "feed_fetched_at": now.isoformat(), "feed_complete": False}
    monkeypatch.setattr(api, "load_snapshot", lambda: snapshot)
    with TestClient(api.app) as client:
        response = client.post("/agent/query", json={"message": "python roles"})
        assert response.status_code == 200
        assert response.json()["results"]["items"] == []
        assert response.json()["tool"] == "search_jobs"


def test_agent_returns_retrieved_job_with_locked_country(provider, monkeypatch, raw_job):
    from datetime import datetime, timedelta, timezone
    from jobcompass.normalize import normalize_job

    now = datetime.now(timezone.utc)
    raw_job["expiryDate"] = int((now + timedelta(days=1)).timestamp())
    row = {**normalize_job(raw_job, now).to_record(), "status": "open", "is_active": True, "status_checked_at": now.isoformat()}
    snapshot = {"records": [row], "attribution": {"label": "Himalayas", "url": "https://himalayas.app"},
                "feed_fetched_at": now.isoformat(), "feed_complete": False}
    monkeypatch.setattr(api, "load_snapshot", lambda: snapshot)
    with TestClient(api.app) as client:
        response = client.post("/agent/query", json={"message": "python roles", "constraints": {"country": "IN"}})
    assert response.status_code == 200
    body = response.json()
    assert body["interpreted_query"]["country"] == "IN"
    assert body["results"]["total"] == 1
    assert body["results"]["items"][0]["application_url"] == raw_job["applicationLink"]
    assert body["results"]["items"][0]["title"] == raw_job["title"]
    assert raw_job["title"] not in json.dumps(provider[0].call_args.kwargs["json"])
