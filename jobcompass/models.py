"""Typed, database-independent job records."""

from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class Job:
    source: str
    source_id: str
    title: str
    company: str
    application_url: str
    excerpt: str | None
    description_html: str | None
    employment_type: str | None
    salary_min: Decimal | None
    salary_max: Decimal | None
    currency: str | None
    salary_period: str | None
    seniority: list[str] | None
    categories: list[str] | None
    location_restrictions: list[dict] | None
    timezone_restrictions: list[float] | None
    source_updated_at: datetime | None
    expires_at: datetime | None
    fetched_at: datetime
    raw_payload: dict
    validation_issues: list[str]

    def to_record(self) -> dict:
        """JSON-safe values: exact decimal strings and UTC ISO dates for storage."""
        record = asdict(self)
        for key, value in record.items():
            if isinstance(value, (Decimal, datetime)):
                record[key] = value.isoformat() if isinstance(value, datetime) else str(value)
        return record
