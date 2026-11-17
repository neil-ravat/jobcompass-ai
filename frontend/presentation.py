"""Formatting only; never infer salaries, scores or eligibility."""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from html import escape
from urllib.parse import urlsplit


def safe_url(value):
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value)
    return value if parsed.scheme in {"https", "http"} and parsed.netloc and not parsed.username and not parsed.password else None


def text(value):
    return escape(str(value), quote=True)


def locations(row):
    restrictions = row.get("location_restrictions")
    if restrictions is None:
        return "Location not specified"
    if restrictions == []:
        return "No country restriction"
    return ", ".join(item.get("name") or item.get("country_code") or "Unspecified" for item in restrictions)


def salary(row):
    values = []
    for key in ("salary_min", "salary_max"):
        value = row.get(key)
        try:
            amount = Decimal(str(value))
            values.append(f"{amount:,.0f}" if amount == amount.to_integral_value() else f"{amount:,.2f}")
        except (InvalidOperation, ValueError):
            values.append(None)
    low, high = values
    if low is None and high is None:
        return "Salary not provided"
    amount = f"{low}–{high}" if low and high and low != high else low or f"Up to {high}"
    if low and not high:
        amount = f"From {low}"
    unit = {"annual": "year", "monthly": "month", "fortnightly": "fortnight", "weekly": "week", "hourly": "hour"}.get(row.get("salary_period"))
    return f"{row.get('currency') or 'Currency unspecified'} {amount}" + (f" / {unit}" if unit else " / period unspecified")


def date_label(value):
    try:
        return datetime.fromisoformat(value).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return "Not provided"


def timezones(row):
    values = row.get("timezone_restrictions")
    if values is None:
        return "Not specified"
    if not values:
        return "No timezone restriction"
    result = []
    for value in values:
        minutes = round(abs(value) * 60)
        result.append(f"UTC{'+' if value >= 0 else '-'}{minutes // 60:02d}:{minutes % 60:02d}")
    return ", ".join(result)
