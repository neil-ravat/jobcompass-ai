import copy
import os

import pytest

from jobcompass import database
from jobcompass.normalize import normalize_job
from jobcompass.semantic import MODEL, content_hash

pytestmark = pytest.mark.database


@pytest.fixture
def db():
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL not configured")
    with database.connect(dsn) as conn:
        assert conn.execute("SELECT current_database()").fetchone()[0].endswith("_test"), "Refusing non-test database"
    database.migrate(dsn)
    with database.connect(dsn) as conn:
        conn.execute("TRUNCATE job_embeddings,jobs,source_snapshots")
    yield dsn
    with database.connect(dsn) as conn:
        conn.execute("TRUNCATE job_embeddings,jobs,source_snapshots")


@pytest.fixture
def snapshot(raw_job, now):
    row = {**normalize_job(raw_job, now).to_record(), "is_active": True, "status": "open",
           "status_checked_at": now.isoformat(), "first_seen_at": now.isoformat(), "last_seen_at": now.isoformat()}
    return {"source": "himalayas", "records": [row], "feed_fetched_at": now.isoformat(),
            "attribution": {"label": "Himalayas", "url": "https://himalayas.app"}, "feed_complete": False}


def test_migrations_and_upserts_are_idempotent(db, snapshot):
    assert database.migrate(db) == []
    assert database.upsert_snapshot(snapshot, db) == 1
    assert database.upsert_snapshot(snapshot, db) == 1
    result = database.read_snapshot(db)
    row = result["records"][0]
    assert row["source_id"] == snapshot["records"][0]["source_id"]
    assert row["application_url"] == snapshot["records"][0]["application_url"]
    assert row["first_seen_at"] == snapshot["records"][0]["first_seen_at"]


def test_sql_vector_search_and_content_invalidation(db, snapshot):
    database.upsert_snapshot(snapshot, db)
    row = snapshot["records"][0]
    vector = [1.0] + [0.0]*383
    database.save_vectors([{**row, "vector": vector, "content_hash": content_hash(row)}], MODEL, db)
    assert database.vector_scores([row], vector, MODEL, db)[(row["source"], row["source_id"])] == pytest.approx(1)
    assert database.vector_scores([{**row, "title": "changed"}], vector, MODEL, db) == {}


def test_invalid_provenance_does_not_write(db, snapshot):
    snapshot["records"][0]["application_url"] = "https://example.invalid/invented"
    with pytest.raises(ValueError, match="provenance"):
        database.upsert_snapshot(snapshot, db)
    with database.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM jobs").fetchone()[0] == 0


def test_closed_status_and_expiry_are_preserved(db, snapshot):
    database.upsert_snapshot(snapshot, db)
    snapshot["records"][0].update(status="closed", is_active=False)
    database.upsert_snapshot(snapshot, db)
    row = database.read_snapshot(db)["records"][0]
    assert row["status"] == "closed" and not row["is_active"]
    assert row["expires_at"] == snapshot["records"][0]["expires_at"]
