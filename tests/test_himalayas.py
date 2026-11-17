"""Offline request, validation, and retry contract checks."""

from unittest.mock import Mock
import secrets

import pytest
import requests

from jobcompass import himalayas


@pytest.fixture
def http_get(monkeypatch):
    response = Mock(spec=requests.Response)
    response.status_code = 200
    response.headers = {}
    response.json.return_value = {"jobs": [], "totalCount": 0}
    get = Mock(return_value=response)
    monkeypatch.setattr(himalayas.requests, "get", get)
    return get


def test_returns_decoded_page_with_source_fields_unchanged(http_get):
    payload = {
        "jobs": [{"guid": "unit-test-only-id", "minSalary": None}],
        "nextCursor": "unit-test-only-cursor",
    }
    http_get.return_value.json.return_value = payload

    assert himalayas.fetch_page(limit=2) == payload
    http_get.assert_called_once_with(
        himalayas.JOBS_ENDPOINT, params={"limit": 2}, timeout=10
    )


def test_empty_jobs_is_a_valid_success(http_get):
    assert himalayas.fetch_page() == {"jobs": [], "totalCount": 0}


@pytest.mark.parametrize("status", [429, 503])
def test_http_errors_are_not_disguised_as_empty_results(http_get, status):
    http_get.return_value.status_code = status
    http_get.return_value.raise_for_status.side_effect = requests.HTTPError(
        f"HTTP {status}"
    )
    with pytest.raises(requests.HTTPError):
        himalayas.fetch_page()
    http_get.return_value.json.assert_not_called()
    assert http_get.call_count == 3


def test_timeout_is_not_disguised_as_empty_results(http_get):
    http_get.side_effect = requests.Timeout("Unit-test timeout")
    with pytest.raises(requests.Timeout):
        himalayas.fetch_page()
    assert http_get.call_count == 3


def test_invalid_json_is_rejected(http_get):
    http_get.return_value.json.side_effect = requests.exceptions.JSONDecodeError(
        "Invalid JSON", "<html>", 0
    )
    with pytest.raises(requests.exceptions.JSONDecodeError):
        himalayas.fetch_page()


@pytest.mark.parametrize("payload", [[], {}, {"jobs": None}, {"jobs": {}}])
def test_invalid_envelope_is_rejected(http_get, payload):
    http_get.return_value.json.return_value = payload
    with pytest.raises(ValueError):
        himalayas.fetch_page()


def test_transient_error_recovers(http_get):
    response = http_get.return_value
    http_get.side_effect = [requests.ConnectionError("temporary"), response]
    assert himalayas.fetch_page()["jobs"] == []
    assert http_get.call_count == 2


def test_rate_limit_honors_retry_after(http_get, monkeypatch):
    response = http_get.return_value
    limited = Mock(spec=requests.Response)
    limited.status_code, limited.headers = 429, {"Retry-After": "7"}
    http_get.side_effect = [limited, response]
    sleep = Mock()
    monkeypatch.setattr(himalayas.time, "sleep", sleep)
    himalayas.fetch_page()
    sleep.assert_called_once_with(7)


def test_long_rate_limit_defers_instead_of_ignoring_header(http_get):
    http_get.return_value.status_code = 429
    http_get.return_value.headers = {"Retry-After": "3600"}
    with pytest.raises(himalayas.RetryDeferred):
        himalayas.fetch_page()
    assert http_get.call_count == 1


def test_retry_after_http_date_is_supported(http_get, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from email.utils import format_datetime

    limited = Mock(spec=requests.Response)
    limited.status_code = 429
    limited.headers = {"Retry-After": format_datetime(datetime.now(timezone.utc) + timedelta(seconds=20))}
    http_get.side_effect = [limited, http_get.return_value]
    sleep = Mock()
    monkeypatch.setattr(himalayas.time, "sleep", sleep)
    himalayas.fetch_page()
    assert 18 <= sleep.call_args.args[0] <= 20


def test_authentication_error_does_not_retry(http_get):
    http_get.return_value.status_code = 401
    http_get.return_value.raise_for_status.side_effect = requests.HTTPError("Unauthorized")
    with pytest.raises(requests.HTTPError):
        himalayas.fetch_page()
    assert http_get.call_count == 1


@pytest.mark.parametrize("cursor", [None, "", 123])
def test_present_invalid_next_cursor_is_not_end_of_feed(http_get, cursor):
    http_get.return_value.json.return_value = {"jobs": [], "nextCursor": cursor}
    with pytest.raises(ValueError, match="nextCursor"):
        himalayas.fetch_page()


def test_cursor_and_optional_key_are_forwarded(http_get, monkeypatch):
    token = secrets.token_urlsafe(24)  # Offline mock only, never sent to a source.
    monkeypatch.setenv("HIMALAYAS_API_KEY", token)
    himalayas.fetch_page(2, "opaque-token")
    http_get.assert_called_once_with(
        himalayas.JOBS_ENDPOINT, timeout=10, params={"limit": 2, "cursor": "opaque-token"},
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.mark.parametrize("limit", [0, 21, True, "3"])
def test_invalid_page_limit_does_not_make_request(http_get, limit):
    with pytest.raises(ValueError):
        himalayas.fetch_page(limit)
    http_get.assert_not_called()


@pytest.mark.parametrize("status", [404, 410])
def test_closed_or_absent_job(http_get, raw_job, status):
    http_get.return_value.status_code = status
    assert himalayas.fetch_job(raw_job["guid"]) is None


def test_job_check_uses_api_and_checks_identity(http_get, raw_job):
    http_get.return_value.json.return_value = {"job": raw_job}
    assert himalayas.fetch_job(raw_job["guid"]) == raw_job
    assert http_get.call_args.args[0].startswith(himalayas.JOBS_ENDPOINT + "/companies/")
    http_get.return_value.json.return_value = {"job": {"guid": "wrong"}}
    with pytest.raises(ValueError, match="identity"):
        himalayas.fetch_job(raw_job["guid"])


def test_job_check_never_requests_an_arbitrary_host(http_get):
    with pytest.raises(ValueError):
        himalayas.fetch_job("https://example.invalid/companies/test/jobs/test")
    http_get.assert_not_called()
