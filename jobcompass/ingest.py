"""Daily feed caching, per-job status checks, and atomic local upserts."""

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from . import himalayas
from .normalize import normalize_job

FEED_TTL = timedelta(hours=24)
STATUS_TTL = timedelta(minutes=10)


def _date(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("Stored timestamps must include a timezone")
    return result


def _load(path):
    if not path.exists():
        return None
    with path.open() as stream:
        return json.load(stream)


def _save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _feed(data_dir, limit, max_pages, now):
    path = data_dir / "himalayas-feed.json"
    cached = _load(path)
    if cached and timedelta(0) <= now - _date(cached["fetched_at"]) < FEED_TTL:
        return cached, True
    jobs, cursors = [], set()
    cursor = None
    for page_number in range(1, max_pages + 1):
        page = himalayas.fetch_page(limit=limit, cursor=cursor)
        jobs.extend(page["jobs"])
        cursor = page.get("nextCursor")
        if cursor is None:
            break
        if cursor in cursors:
            raise ValueError("Repeated pagination cursor; feed not saved")
        cursors.add(cursor)
    feed = {
        "fetched_at": now.isoformat(), "jobs": jobs,
        "complete": cursor is None, "pages": page_number,
        "limit": limit, "max_pages": max_pages,
        "total_count": page.get("totalCount"),
    }
    _save(path, feed)
    return feed, False


def ingest(data_dir: Path, limit=20, max_pages=1, now=None) -> dict:
    """Ingest real API data. Tests replace the client; runtime never uses fixtures."""
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")
    if type(max_pages) is not int or max_pages < 1:
        raise ValueError("max_pages must be a positive integer")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must include a timezone")
    now = now.astimezone(timezone.utc)
    data_dir = Path(data_dir)
    previous = _load(data_dir / "jobs.json") or {"records": []}
    records = {(row["source"], row["source_id"]): row for row in previous["records"]}
    feed, cache_used = _feed(data_dir, limit, max_pages, now)
    fetched_at = _date(feed["fetched_at"])
    candidates, rejected = {}, []
    duplicates = 0
    for index, raw in enumerate(feed["jobs"]):
        try:
            job = normalize_job(raw, fetched_at)
        except (ValueError, TypeError) as error:
            rejected.append({"index": index, "source_id": raw.get("guid") if isinstance(raw, dict) else None, "reason": str(error)})
            continue
        key = (job.source, job.source_id)
        if key in candidates:
            duplicates += 1
            epoch = datetime.min.replace(tzinfo=timezone.utc)
            if (job.source_updated_at or epoch) <= (candidates[key].source_updated_at or epoch):
                continue
        candidates[key] = job

    status_errors = []
    for key, job in candidates.items():
        old = records.get(key, {})
        checked = old.get("status_checked_at")
        status = "unverified"
        if job.expires_at is not None and job.expires_at <= now:
            status = "expired"
        elif checked and timedelta(0) <= now - _date(checked) < STATUS_TTL:
            status = old["status"]
            # Keep newer detail content when the daily feed is older.
            if old.get("raw_payload") and _date(old["fetched_at"]) >= job.fetched_at:
                job = normalize_job(old["raw_payload"], _date(old["fetched_at"]))
            if status == "unverified":
                status_errors.append({"source_id": job.source_id, "reason": "Recent status check failed; retry after ten minutes."})
        else:
            checked = now.isoformat()
            try:
                current = himalayas.fetch_job(job.source_id)
                if current is None:
                    status = "closed"
                else:
                    job = normalize_job(current, now)
                    status = "expired" if job.expires_at and job.expires_at <= now else "open"
            except himalayas.RetryDeferred:
                # Stop the entire run rather than hitting another job immediately.
                raise
            except requests.HTTPError as error:
                if error.response is not None and error.response.status_code in {401, 403, 429}:
                    raise
                status_errors.append({"source_id": job.source_id, "reason": str(error)})
            except (requests.RequestException, ValueError, TypeError) as error:
                status_errors.append({"source_id": job.source_id, "reason": str(error)})
        if job.expires_at is not None and job.expires_at <= now:
            status = "expired"
        row = job.to_record()
        row.update({
            "first_seen_at": old.get("first_seen_at", now.isoformat()),
            "last_seen_at": max(old.get("last_seen_at", ""), job.fetched_at.isoformat()),
            "status_checked_at": checked, "status": status, "is_active": status == "open",
        })
        records[key] = row

    reconciled = feed["complete"] and not rejected and not status_errors
    for key, row in records.items():
        if row.get("expires_at") and _date(row["expires_at"]) <= now:
            row.update(status="expired", is_active=False)
        elif key not in candidates:
            if reconciled:
                row.update(status="missing_from_feed", is_active=False)
            elif not row.get("status_checked_at") or now - _date(row["status_checked_at"]) >= STATUS_TTL:
                row.update(status="unverified", is_active=False)

    rows = [records[key] for key in sorted(records)]
    result = {
        "schema_version": 1, "source": "himalayas",
        "attribution": {"label": "Jobs sourced from Himalayas", "url": "https://himalayas.app"},
        "run_at": now.isoformat(), "feed_fetched_at": feed["fetched_at"],
        "feed_cache_used": cache_used, "feed_complete": feed["complete"],
        "missing_jobs_reconciled": reconciled,
        "scope": {"pages": feed["pages"], "limit": feed["limit"], "max_pages": feed["max_pages"]},
        "counts": {
            "fetched": len(feed["jobs"]), "accepted_unique": len(candidates),
            "rejected": len(rejected), "duplicates": duplicates,
            "stored": len(rows), "active": sum(row["is_active"] for row in rows),
            "expired": sum(row["status"] == "expired" for row in rows),
            "closed": sum(row["status"] == "closed" for row in rows),
            "unverified": sum(row["status"] == "unverified" for row in rows),
        },
        "status_errors": status_errors, "rejected_records": rejected, "records": rows,
    }
    _save(data_dir / "jobs.json", result)
    return result
