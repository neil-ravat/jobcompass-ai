from datetime import timedelta

import pytest
from pydantic import ValidationError

from jobcompass.normalize import normalize_job
from jobcompass.search import SearchParams, country_eligibility, filter_jobs, rank_jobs


@pytest.fixture
def row(raw_job, now):
    return {**normalize_job(raw_job, now).to_record(), "is_active": True, "status": "open", "status_checked_at": now.isoformat()}


def test_country_states_and_codes(row, now):
    assert country_eligibility(row, "IN") == "eligible"
    assert country_eligibility(row, "US") == "ineligible"
    assert SearchParams(country="India").country == "IN"
    row["location_restrictions"] = None
    assert country_eligibility(row, "IN") == "unknown"
    assert not filter_jobs([row], SearchParams(country="IN"), now)
    row["location_restrictions"] = []
    assert country_eligibility(row, "IN") == "unrestricted"
    assert filter_jobs([row], SearchParams(country="IN"), now)


def test_salary_constraint_requires_known_matching_units(row, now):
    params = SearchParams(min_salary=100, currency="USD", salary_period="annual")
    assert not filter_jobs([row], params, now)
    row.update(salary_min="100", salary_max="200", currency="USD", salary_period="annual")
    assert filter_jobs([row], params, now)
    for change in ({"currency": "INR"}, {"salary_period": "hourly"}, {"salary_min": "99"}):
        assert not filter_jobs([{**row, **change}], params, now)


@pytest.mark.parametrize("kwargs", [{"country": "Atlantis"}, {"q": " "}, {"limit": 101},
    {"offset": -1}, {"min_salary": 10}, {"min_salary": "NaN"}, {"currency": "ZZZ"}, {"oops": True}, {"q": "!!!"}])
def test_invalid_constraints(kwargs):
    with pytest.raises(ValidationError):
        SearchParams(**kwargs)


def test_keyword_role_and_remote_filters(row, now):
    assert filter_jobs([row], SearchParams(q="python", role="developer"), now)
    assert not filter_jobs([row], SearchParams(role="designer"), now)
    assert not filter_jobs([row], SearchParams(q="javascript"), now)
    assert not filter_jobs([{**row, "source": "unknown"}], SearchParams(), now)
    assert filter_jobs([{**row, "source": "unknown"}], SearchParams(remote_only=False), now)


def test_title_beats_body_and_ties_are_stable(row):
    title = {**row, "source_id": "b", "title": "Python engineer", "description_html": "Other"}
    body = {**row, "source_id": "c", "title": "Engineer", "description_html": "Python"}
    tie = {**title, "source_id": "a"}
    ranked = rank_jobs([title, body, tie], "python")
    assert [job["source_id"] for job in ranked] == ["a", "b", "c"]
    assert ranked[0]["score_components"] == {"title": 60, "description": 0, "categories": 0}
    assert ranked == rank_jobs([body, tie, title], "python")


def test_expired_closed_and_stale_rows_are_excluded(row, now):
    changes = [{"expires_at": now.isoformat()}, {"is_active": False},
               {"status_checked_at": (now - timedelta(minutes=11)).isoformat()}]
    for change in changes:
        assert not filter_jobs([{**row, **change}], SearchParams(), now)


def test_currency_and_period_are_constraints_even_without_floor(row, now):
    assert not filter_jobs([row], SearchParams(currency="USD"), now)
    row.update(currency="USD", salary_period="annual")
    assert filter_jobs([row], SearchParams(currency="USD", salary_period="annual"), now)
    assert not filter_jobs([row], SearchParams(salary_period="hourly"), now)


def test_explicit_nonremote_status_overrides_remote_source(row, now):
    assert not filter_jobs([{**row, "remote_type": "onsite"}], SearchParams(), now)
