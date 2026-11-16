"""Read the real ingestion snapshot; no network or fabricated fallback on reads."""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .search import current_job


class StoreUnavailable(RuntimeError):
    pass


def load_snapshot():
    path = Path(os.environ.get("JOBCOMPASS_DATA_DIR", "data")) / "jobs.json"
    try:
        if os.environ.get("DATABASE_URL"):
            try:
                from .database import read_snapshot
                snapshot = read_snapshot()
            except Exception as error:
                raise StoreUnavailable("PostgreSQL unavailable or not initialized. Check database configuration and migrations.") from error
        else:
            snapshot = json.loads(path.read_text())
        fetched = datetime.fromisoformat(snapshot["feed_fetched_at"])
        now = datetime.now(timezone.utc)
        if fetched.tzinfo is None or not timedelta(0) <= now - fetched < timedelta(hours=24):
            raise StoreUnavailable("Feed is stale. Run python -m jobcompass to refresh it.")
        if not isinstance(snapshot["records"], list):
            raise ValueError("records must be a list")
        for row in snapshot["records"]:
            if not isinstance(row, dict) or not all(isinstance(row.get(key), str) and row[key]
                    for key in ("source", "source_id", "title", "company", "application_url")):
                raise ValueError("Invalid normalized job")
        open_rows = [row for row in snapshot["records"] if row.get("is_active")]
        if snapshot.get("status_errors") and not any(current_job(row, now) for row in snapshot["records"]):
            raise StoreUnavailable("Job status verification failed. Run python -m jobcompass to retry.")
        if open_rows and not any(current_job(row, now) for row in open_rows):
            raise StoreUnavailable("Job status needs refreshing. Run python -m jobcompass.")
        return snapshot
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise StoreUnavailable("Job snapshot is missing or invalid. Run python -m jobcompass.") from error
