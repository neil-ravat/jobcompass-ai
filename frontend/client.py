"""Small HTTP boundary. No database, source-API or model access from the UI."""

import os
from urllib.parse import urlsplit

import requests

ENDPOINTS = {"Keyword match": "/recommendations", "Semantic match": "/search", "Browse jobs": "/jobs"}


class APIError(RuntimeError):
    pass


def api_url():
    value = os.environ.get("JOBCOMPASS_API_URL", "http://127.0.0.1:8765").rstrip("/")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise APIError("The job service address is invalid. Check JOBCOMPASS_API_URL.")
    return value


def get_json(path, params=None):
    try:
        response = requests.get(api_url() + path, params=params, timeout=(3, 45))
    except requests.Timeout:
        raise APIError("The job service took too long to respond. Try again in a moment.") from None
    except requests.RequestException:
        raise APIError("Cannot reach the job service. Start the local backend, then retry.") from None
    try:
        payload = response.json()
    except ValueError:
        raise APIError("The job service returned an unreadable response. Retry or check the backend.") from None
    if not response.ok:
        if response.status_code == 422:
            raise APIError("Check your search filters. A minimum salary requires a currency and pay period.")
        if response.status_code == 503 and isinstance(payload, dict) and payload.get("code") == "semantic_unavailable":
            raise APIError("Semantic search is unavailable. Try Keyword match while the search index is refreshed.")
        if response.status_code == 503:
            raise APIError("Job data is not ready or needs refreshing. Let the refresh worker finish, then retry.")
        raise APIError(f"The job service could not complete this search (HTTP {response.status_code}). Try again.")
    if not isinstance(payload, dict):
        raise APIError("The job service returned an unexpected response.")
    return payload


def search(mode, params):
    payload = get_json(ENDPOINTS[mode], params)
    if (not isinstance(payload.get("items"), list) or type(payload.get("total")) is not int
            or payload["total"] < 0 or not isinstance(payload.get("attribution"), dict)):
        raise APIError("The job service returned an invalid results page.")
    for item in payload["items"]:
        if not isinstance(item, dict) or not all(isinstance(item.get(key), str) and item[key]
                for key in ("source", "source_id", "title", "company", "application_url")):
            raise APIError("The job service returned an incomplete job record.")
    return payload


def search_params(values, offset=0, limit=10):
    """Translate UI choices, leaving eligibility and ranking to the backend."""
    params = {"remote_only": values["remote_only"], "limit": limit, "offset": offset}
    for key in ("q", "role", "country", "currency", "salary_period"):
        value = values.get(key)
        if value and str(value).strip():
            params[key] = str(value).strip()
    if values.get("min_salary") is not None:
        if not params.get("currency") or not params.get("salary_period"):
            raise ValueError("Choose a currency and pay period for your minimum salary.")
        params["min_salary"] = values["min_salary"]
    if values["mode"] == "Semantic match" and not params.get("q"):
        raise ValueError("Enter a keyword or describe the work you want for semantic search.")
    return params
