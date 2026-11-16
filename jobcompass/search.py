"""Hard constraints first, then transparent and deterministic relevance scores."""

import html
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal

import pycountry
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SearchParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    q: str | None = Field(default=None, max_length=300)
    role: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=100)
    remote_only: bool = True
    min_salary: Decimal | None = Field(default=None, ge=0, le=10**12, allow_inf_nan=False)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    salary_period: Literal["hourly", "weekly", "fortnightly", "monthly", "annual"] | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @field_validator("q", "role", "country")
    @classmethod
    def nonblank(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Must not be blank")
        return value

    @field_validator("country")
    @classmethod
    def valid_country(cls, value):
        if value is None:
            return None
        try:
            return pycountry.countries.lookup(value).alpha_2
        except LookupError:
            raise ValueError("Use an ISO country code or recognized country name") from None

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value):
        if value is not None:
            value = value.upper()
            if pycountry.currencies.get(alpha_3=value) is None:
                raise ValueError("Unknown ISO currency code")
        return value

    @model_validator(mode="after")
    def salary_units(self):
        if self.min_salary is not None and (self.currency is None or self.salary_period is None):
            raise ValueError("min_salary requires currency and salary_period")
        return self


def tokens(text):
    return set(re.findall(r"[\w]+(?:[+#]+)?", text.casefold()))


def description_text(row):
    return html.unescape(re.sub(r"<[^>]+>", " ", row.get("description_html") or row.get("excerpt") or ""))


def country_eligibility(row, country):
    locations = row.get("location_restrictions")
    if locations is None:
        return "unknown"
    if locations == []:
        return "unrestricted"
    if not country:
        return "restricted"
    unknown = False
    for location in locations:
        try:
            code = pycountry.countries.lookup(location.get("country_code") or location["name"]).alpha_2
        except (LookupError, KeyError, AttributeError, TypeError):
            unknown = True
            continue
        if code == country:
            return "eligible"
    return "unknown" if unknown else "ineligible"


def current_job(row, now):
    try:
        checked = datetime.fromisoformat(row["status_checked_at"])
        expires = datetime.fromisoformat(row["expires_at"]) if row.get("expires_at") else None
        return (
            row.get("is_active") is True and row.get("status") == "open"
            and checked.tzinfo is not None
            and timedelta(0) <= now - checked < timedelta(minutes=10)
            and (expires is None or (expires.tzinfo is not None and expires > now))
        )
    except (KeyError, ValueError, TypeError):
        return False


def filter_jobs(records, params, now=None, keyword_mode="all"):
    now = now or datetime.now(timezone.utc)
    query = tokens(params.q or "")
    role = tokens(params.role or "")
    results = []
    for row in records:
        if not current_job(row, now):
            continue
        # Himalayas advertises remote jobs; this does not imply worldwide eligibility.
        remote = row.get("remote_type") == "remote" or row.get("source") == "himalayas"
        if params.remote_only and not remote:
            continue
        eligibility = country_eligibility(row, params.country)
        if params.country and eligibility not in {"eligible", "unrestricted"}:
            continue
        if role and not role <= tokens(row.get("title", "")):
            continue
        if params.min_salary is not None:
            try:
                amount = Decimal(str(row.get("salary_min")))
                if not amount.is_finite() or amount < params.min_salary:
                    continue
            except (InvalidOperation, ValueError):
                continue
            if row.get("currency") != params.currency or row.get("salary_period") != params.salary_period:
                continue
        document = tokens(" ".join([row.get("title", ""), description_text(row), " ".join(row.get("categories") or [])]))
        if query and keyword_mode == "all" and not query <= document:
            continue
        if query and keyword_mode == "any" and not query & document:
            continue
        results.append({**row, "country_eligibility": eligibility, "remote": remote})
    return results


def rank_jobs(records, query=None):
    query_tokens = tokens(query or "")
    result = []
    for row in records:
        fields = {"title": tokens(row["title"]), "description": tokens(description_text(row)),
                  "categories": tokens(" ".join(row.get("categories") or []))}
        components = {key: round(weight * len(query_tokens & fields[key]) / len(query_tokens), 6) if query_tokens else 0.0
                      for key, weight in (("title", 60), ("description", 30), ("categories", 10))}
        result.append({**row, "score": round(sum(components.values()), 6), "score_components": components,
                       "matched_terms": sorted(query_tokens & set.union(*fields.values()))})
    # Stable across source order and repeated queries, including equal scores/dates.
    result.sort(key=lambda row: (row["source"], row["source_id"]))
    result.sort(key=lambda row: row.get("source_updated_at") or "", reverse=True)
    result.sort(key=lambda row: row["score"], reverse=True)
    return result
