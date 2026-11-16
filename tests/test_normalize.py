from decimal import Decimal

import pytest

from jobcompass.normalize import normalize_job


def test_preserves_identity_links_nulls_and_raw_data(raw_job, now):
    job = normalize_job(raw_job, now)
    assert job.source == "himalayas"
    assert job.source_id == raw_job["guid"]
    assert job.application_url == raw_job["applicationLink"]
    assert job.salary_min is None
    assert job.raw_payload == raw_job
    assert job.location_restrictions == [{"name": "India", "country_code": None}]
    assert job.timezone_restrictions == [5.5]
    assert job.source_updated_at == now


def test_documented_schema_variants(raw_job, now):
    raw_job.update(locationRestrictions=[{"alpha2": "IN", "name": "India", "slug": "india"}],
                   timezoneRestrictions=["UTC+5:30", "UTC-3:30", "UTC"], seniority="Junior")
    job = normalize_job(raw_job, now)
    assert job.location_restrictions == [{"name": "India", "country_code": "IN"}]
    assert job.timezone_restrictions == [5.5, -3.5, 0]
    assert job.seniority == ["Junior"]


def test_missing_restrictions_are_not_worldwide(raw_job, now):
    del raw_job["locationRestrictions"]
    assert normalize_job(raw_job, now).location_restrictions is None
    raw_job["locationRestrictions"] = []
    assert normalize_job(raw_job, now).location_restrictions == []
    raw_job["locationRestrictions"] = [None]
    job = normalize_job(raw_job, now)
    assert job.location_restrictions is None
    assert job.validation_issues


@pytest.mark.parametrize("field", ["guid", "applicationLink", "title", "companyName"])
@pytest.mark.parametrize("value", [None, "", 42])
def test_invalid_required_values_reject_record(raw_job, now, field, value):
    raw_job[field] = value
    with pytest.raises(ValueError):
        normalize_job(raw_job, now)


@pytest.mark.parametrize("url", ["javascript:alert(1)", "https://u:p@example.com", "https://example.com/a b", "https://example.com:bad", " https://example.com"])
def test_invalid_apply_url(raw_job, now, url):
    raw_job["applicationLink"] = url
    with pytest.raises(ValueError):
        normalize_job(raw_job, now)


def test_decimal_and_datetime_serialization(raw_job, now):
    raw_job.update(minSalary="10.25", maxSalary=20, currency="INR", salaryPeriod="hourly")
    job = normalize_job(raw_job, now)
    assert job.salary_min == Decimal("10.25")
    assert job.to_record()["salary_min"] == "10.25"
    assert job.to_record()["source_updated_at"] == now.isoformat()
    assert job.currency == "INR" and job.salary_period == "hourly"


@pytest.mark.parametrize("field,value", [
    ("minSalary", True), ("minSalary", -1), ("minSalary", "NaN"),
    ("expiryDate", "tomorrow"), ("expiryDate", 10**30),
    ("timezoneRestrictions", [True]), ("timezoneRestrictions", [25]),
    ("currency", "rupees"), ("categories", "Python"),
])
def test_malformed_optional_values_have_diagnostics(raw_job, now, field, value):
    raw_job[field] = value
    job = normalize_job(raw_job, now)
    assert any(field in issue for issue in job.validation_issues)
    assert job.raw_payload[field] == value


def test_inverted_salary_range_is_unknown(raw_job, now):
    raw_job.update(minSalary=20, maxSalary=10)
    job = normalize_job(raw_job, now)
    assert job.salary_min is None and job.salary_max is None
    assert job.validation_issues
