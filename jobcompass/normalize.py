"""Pure normalization: unknown optional values stay unknown, with diagnostics."""

import json
import math
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from .himalayas import job_api_url
from .models import Job


def normalize_job(raw: dict, fetched_at: datetime) -> Job:
    if not isinstance(raw, dict):
        raise ValueError("Job must be a JSON object")
    # Reject non-JSON values instead of losing the original payload at persistence.
    json.dumps(raw, allow_nan=False)
    if fetched_at.tzinfo is None:
        raise ValueError("fetched_at must include a timezone")
    issues = []

    def text(field, required=False):
        value = raw.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if required:
            raise ValueError(f"Missing or invalid required field: {field}")
        if value is not None:
            issues.append(f"{field}: expected nonempty text")
        return None

    def optional(field, parser):
        value = raw.get(field)
        if value is None:
            return None
        try:
            return parser(value)
        except (ValueError, TypeError, InvalidOperation, OverflowError, OSError):
            issues.append(f"{field}: invalid value retained in raw_payload")
            return None

    source_id = text("guid", required=True)
    if source_id != raw["guid"]:
        raise ValueError("guid must not contain surrounding whitespace")
    job_api_url(source_id)
    application_url = text("applicationLink", required=True)
    if application_url != raw["applicationLink"]:
        raise ValueError("applicationLink must not contain surrounding whitespace")
    parsed = urlsplit(application_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or any(char.isspace() or ord(char) < 32 for char in application_url)
    ):
        raise ValueError("Invalid applicationLink")
    parsed.port  # Reject a malformed port without rewriting any URL component.
    low = optional("minSalary", _salary)
    high = optional("maxSalary", _salary)
    if low is not None and high is not None and low > high:
        issues.append("salary: minimum exceeds maximum")
        low = high = None
    return Job(
        source="himalayas", source_id=source_id,
        title=text("title", required=True), company=text("companyName", required=True),
        application_url=application_url,
        excerpt=text("excerpt"), description_html=text("description"),
        employment_type=text("employmentType"), salary_min=low, salary_max=high,
        currency=optional("currency", _currency),
        salary_period=optional("salaryPeriod", _salary_period),
        seniority=optional("seniority", lambda value: _strings([value] if isinstance(value, str) else value)),
        categories=optional("categories", _strings),
        location_restrictions=optional("locationRestrictions", _locations),
        timezone_restrictions=optional("timezoneRestrictions", _timezones),
        source_updated_at=optional("pubDate", _timestamp),
        expires_at=optional("expiryDate", _timestamp),
        fetched_at=fetched_at.astimezone(timezone.utc), raw_payload=raw,
        validation_issues=issues,
    )


def _salary(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("Invalid salary")
    amount = Decimal(str(value))
    if not amount.is_finite() or amount < 0:
        raise ValueError("Invalid salary")
    return amount


def _currency(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z]{3}", value):
        raise ValueError("Invalid currency code")
    return value


def _salary_period(value):
    if value not in ("hourly", "weekly", "fortnightly", "monthly", "annual"):
        raise ValueError("Invalid salary period")
    return value


def _strings(value):
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError("Expected nonempty strings in a list")
    return list(dict.fromkeys(item.strip() for item in value))


def _locations(value):
    if not isinstance(value, list):
        raise ValueError("Expected locations list")
    result = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append({"name": item.strip(), "country_code": None})
        elif isinstance(item, dict):
            name, code = item.get("name"), item.get("alpha2")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Invalid country name")
            if not isinstance(code, str) or not re.fullmatch(r"[A-Z]{2}", code):
                raise ValueError("Invalid country code")
            result.append({"name": name.strip(), "country_code": code})
        else:
            raise ValueError("Unknown location shape")
    return result


def _timezones(value):
    if not isinstance(value, list):
        raise ValueError("Expected timezone list")
    result = []
    for item in value:
        if type(item) in (int, float):
            offset = float(item)
        elif item == "UTC":
            offset = 0.0
        elif isinstance(item, str) and (match := re.fullmatch(r"UTC([+-])(\d{1,2})(?::([0-5]\d))?", item)):
            sign, hours, minutes = match.groups()
            offset = (int(hours) + int(minutes or 0) / 60) * (-1 if sign == "-" else 1)
        else:
            raise ValueError("Unknown timezone shape")
        if not math.isfinite(offset) or not -12 <= offset <= 14:
            raise ValueError("Invalid timezone offset")
        result.append(offset)
    return list(dict.fromkeys(result))


def _timestamp(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Expected Unix seconds")
    return datetime.fromtimestamp(value, timezone.utc)
