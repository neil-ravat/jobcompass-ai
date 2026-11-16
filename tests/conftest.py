"""All tests are offline; synthetic listings exist only in this directory."""

from datetime import datetime, timedelta, timezone

import pytest
import requests

from jobcompass import himalayas


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delattr(requests.sessions.Session, "request")
    monkeypatch.delenv("HIMALAYAS_API_KEY", raising=False)
    monkeypatch.setattr(himalayas, "_wait_for_slot", lambda: None)
    monkeypatch.setattr(himalayas.time, "sleep", lambda delay: None)


@pytest.fixture
def now():
    return datetime(2026, 11, 17, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def raw_job(now):
    return {
        "guid": "https://himalayas.app/companies/unit-test/jobs/python-test",
        "applicationLink": "https://himalayas.app/companies/unit-test/jobs/python-test?utm_source=api",
        "title": "Test-only Python developer", "companyName": "Unit test employer",
        "minSalary": None, "maxSalary": None,
        "locationRestrictions": ["India"], "timezoneRestrictions": [5.5],
        "seniority": ["Entry-level"],
        "pubDate": int(now.timestamp()),
        "expiryDate": int((now + timedelta(days=2)).timestamp()),
    }
