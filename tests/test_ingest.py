import copy
import json
from datetime import timedelta
from unittest.mock import Mock

import pytest
import requests

from jobcompass import himalayas
from jobcompass.ingest import ingest


def clients(monkeypatch, raw_job, complete=True):
    page = {"jobs": [raw_job]}
    if not complete:
        page["nextCursor"] = "next-page"
    browse = Mock(return_value=page)
    detail = Mock(return_value=raw_job)
    monkeypatch.setattr(himalayas, "fetch_page", browse)
    monkeypatch.setattr(himalayas, "fetch_job", detail)
    return browse, detail


def test_real_pipeline_contract_cache_and_idempotence(tmp_path, monkeypatch, raw_job, now):
    browse, detail = clients(monkeypatch, raw_job)
    first = ingest(tmp_path, now=now)
    second = ingest(tmp_path, now=now + timedelta(minutes=1))
    assert first["counts"]["stored"] == second["counts"]["stored"] == 1
    assert first["records"][0]["first_seen_at"] == second["records"][0]["first_seen_at"]
    assert second["feed_cache_used"]
    assert browse.call_count == detail.call_count == 1
    assert second["counts"]["active"] == 1
    assert json.loads((tmp_path / "jobs.json").read_text()) == second


def test_status_refreshes_after_ten_minutes_without_feed_poll(tmp_path, monkeypatch, raw_job, now):
    browse, detail = clients(monkeypatch, raw_job)
    ingest(tmp_path, now=now)
    detail.return_value = None
    result = ingest(tmp_path, now=now + timedelta(minutes=11))
    assert browse.call_count == 1 and detail.call_count == 2
    assert result["counts"]["active"] == 0
    assert result["records"][0]["status"] == "closed"


def test_duplicate_keeps_latest_record(tmp_path, monkeypatch, raw_job, now):
    browse, detail = clients(monkeypatch, raw_job)
    newer = copy.deepcopy(raw_job)
    newer.update(title="Updated test title", pubDate=int(now.timestamp()) + 1)
    browse.return_value = {"jobs": [raw_job, newer]}
    detail.return_value = newer
    result = ingest(tmp_path, now=now)
    assert result["counts"]["duplicates"] == 1
    assert result["counts"]["stored"] == 1
    assert result["records"][0]["title"] == newer["title"]
    detail.assert_called_once()


def test_expired_records_skip_detail_request(tmp_path, monkeypatch, raw_job, now):
    raw_job["expiryDate"] = int(now.timestamp())
    _, detail = clients(monkeypatch, raw_job)
    result = ingest(tmp_path, now=now)
    assert result["counts"]["expired"] == 1 and result["counts"]["active"] == 0
    detail.assert_not_called()


def test_cached_details_can_expire_before_status_ttl(tmp_path, monkeypatch, raw_job, now):
    browse, detail = clients(monkeypatch, raw_job)
    shorter = copy.deepcopy(raw_job)
    shorter["expiryDate"] = int((now + timedelta(minutes=2)).timestamp())
    detail.return_value = shorter
    ingest(tmp_path, now=now)
    result = ingest(tmp_path, now=now + timedelta(minutes=3))
    assert result["counts"]["active"] == 0
    assert result["counts"]["expired"] == 1


def test_pagination_echoes_cursor_and_marks_cap_partial(tmp_path, monkeypatch, raw_job, now):
    browse, _ = clients(monkeypatch, raw_job)
    browse.side_effect = [{"jobs": [raw_job], "nextCursor": "opaque"}, {"jobs": [], "nextCursor": "more"}]
    result = ingest(tmp_path, max_pages=2, now=now)
    assert browse.call_args_list[1].kwargs["cursor"] == "opaque"
    assert not result["feed_complete"] and not result["missing_jobs_reconciled"]


def test_repeated_cursor_does_not_replace_snapshot(tmp_path, monkeypatch, raw_job, now):
    browse, _ = clients(monkeypatch, raw_job)
    browse.return_value = {"jobs": [raw_job], "nextCursor": "same"}
    with pytest.raises(ValueError, match="Repeated"):
        ingest(tmp_path, max_pages=2, now=now)
    assert not (tmp_path / "jobs.json").exists()
    assert not (tmp_path / "himalayas-feed.json").exists()


@pytest.mark.parametrize("complete,invalid,expected", [(True, False, "missing_from_feed"), (False, False, "unverified"), (True, True, "unverified")])
def test_only_complete_valid_feed_retires_missing_jobs(tmp_path, monkeypatch, raw_job, now, complete, invalid, expected):
    browse, _ = clients(monkeypatch, raw_job)
    ingest(tmp_path, now=now)
    page = {"jobs": [None] if invalid else []}
    if not complete:
        page["nextCursor"] = "more"
    browse.return_value = page
    result = ingest(tmp_path, now=now + timedelta(hours=25))
    assert result["records"][0]["status"] == expected
    assert not result["records"][0]["is_active"]


def test_failed_feed_refresh_keeps_previous_snapshot(tmp_path, monkeypatch, raw_job, now):
    browse, _ = clients(monkeypatch, raw_job)
    ingest(tmp_path, now=now)
    previous = (tmp_path / "jobs.json").read_bytes()
    browse.side_effect = requests.Timeout("Source unavailable")
    with pytest.raises(requests.Timeout):
        ingest(tmp_path, now=now + timedelta(hours=25))
    assert (tmp_path / "jobs.json").read_bytes() == previous


def test_unverified_job_is_withheld_and_failure_visible(tmp_path, monkeypatch, raw_job, now):
    _, detail = clients(monkeypatch, raw_job)
    detail.side_effect = requests.Timeout("status request timed out")
    result = ingest(tmp_path, now=now)
    assert result["counts"]["unverified"] == 1
    assert result["counts"]["active"] == 0
    assert result["status_errors"]
    assert not result["missing_jobs_reconciled"]


def test_bad_optional_value_does_not_drop_valid_record(tmp_path, monkeypatch, raw_job, now):
    raw_job["minSalary"] = "undisclosed"
    clients(monkeypatch, raw_job)
    result = ingest(tmp_path, now=now)
    assert result["counts"]["accepted_unique"] == 1
    assert result["records"][0]["validation_issues"]


def test_rate_limited_status_stops_run_and_preserves_snapshot(tmp_path, monkeypatch, raw_job, now):
    _, detail = clients(monkeypatch, raw_job)
    ingest(tmp_path, now=now)
    original = (tmp_path / "jobs.json").read_bytes()
    detail.side_effect = himalayas.RetryDeferred("Wait until tomorrow")
    with pytest.raises(himalayas.RetryDeferred):
        ingest(tmp_path, now=now + timedelta(minutes=11))
    assert (tmp_path / "jobs.json").read_bytes() == original
