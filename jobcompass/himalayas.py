"""Small synchronous client for the official Himalayas APIs."""

import os
import random
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import requests

JOBS_ENDPOINT = "https://himalayas.app/jobs/api"
MAX_ATTEMPTS = 3
MAX_RETRY_WAIT = 30
_last_request_at = None


class RetryDeferred(requests.RequestException):
    """The source asked us to wait longer than this short CLI run allows."""


def _wait_for_slot():
    global _last_request_at
    if _last_request_at is not None:
        time.sleep(max(0, 1.05 - (time.monotonic() - _last_request_at)))
    _last_request_at = time.monotonic()


def _retry_delay(response, attempt):
    value = response.headers.get("Retry-After") if response is not None else None
    if value:
        try:
            delay = float(value)
            if not 0 <= delay < float("inf"):
                raise ValueError("Invalid delay")
        except ValueError:
            try:
                when = parsedate_to_datetime(value)
                if when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
                delay = max(0, (when - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                delay = 2**attempt + random.uniform(0, 0.25)
    else:
        delay = 2**attempt + random.uniform(0, 0.25)
    if delay > MAX_RETRY_WAIT:
        raise RetryDeferred(f"Source requested a {delay:.0f}s wait; try again later.")
    return delay


def _request(url, **kwargs):
    key = os.environ.get("HIMALAYAS_API_KEY")
    if key:
        kwargs["headers"] = {"Authorization": f"Bearer {key}"}
    for attempt in range(MAX_ATTEMPTS):
        _wait_for_slot()
        try:
            response = requests.get(url, timeout=10, **kwargs)
        except (requests.Timeout, requests.ConnectionError):
            if attempt == MAX_ATTEMPTS - 1:
                raise
            time.sleep(_retry_delay(None, attempt))
            continue
        if response.status_code in {429, 500, 502, 503, 504}:
            if attempt < MAX_ATTEMPTS - 1:
                time.sleep(_retry_delay(response, attempt))
                continue
        return response
    raise RuntimeError("Unreachable retry state")


def fetch_page(limit: int = 3, cursor: str | None = None) -> dict:
    """Fetch one validated envelope; never turn an API failure into an empty feed."""
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("limit must be an integer between 1 and 20")
    params = {"limit": limit}
    if cursor is not None:
        if not isinstance(cursor, str) or not cursor:
            raise ValueError("cursor must be a nonempty string")
        params["cursor"] = cursor
    response = _request(JOBS_ENDPOINT, params=params)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise ValueError("Expected a JSON object containing a jobs list")
    if "nextCursor" in payload and (
        not isinstance(payload["nextCursor"], str) or not payload["nextCursor"]
    ):
        raise ValueError("Invalid nextCursor; refusing to assume the feed ended")
    return payload


def job_api_url(guid: str) -> str:
    """Build only the documented API URL, never fetch arbitrary source URLs."""
    parsed = urlsplit(guid)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "himalayas.app"
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(r"/companies/[a-zA-Z0-9_-]+/jobs/[a-zA-Z0-9_-]+", parsed.path)
    ):
        raise ValueError("Invalid Himalayas guid URL")
    return JOBS_ENDPOINT + parsed.path


def fetch_job(guid: str) -> dict | None:
    """Return a currently open job; None means the source returned 404 or 410."""
    response = _request(job_api_url(guid))
    if response.status_code in {404, 410}:
        return None
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("job"), dict):
        raise ValueError("Expected a JSON object containing a job object")
    if payload["job"].get("guid") != guid:
        raise ValueError("Job status response has a different source identity")
    return payload["job"]
