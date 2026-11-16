"""Parameterized PostgreSQL persistence and pgvector exact cosine queries."""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path


def connect(dsn=None):
    try:
        import psycopg
    except ImportError as error:
        raise RuntimeError("Install the postgres extra to use DATABASE_URL") from error
    dsn = dsn or os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(dsn, connect_timeout=5)


def migrate(dsn=None):
    applied = []
    with connect(dsn) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(174204)")
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())")
        for path in sorted((Path(__file__).resolve().parent.parent / "migrations").glob("*.sql")):
            sql = path.read_text()
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            previous = conn.execute("SELECT checksum FROM schema_migrations WHERE version=%s", (path.name,)).fetchone()
            if previous:
                if previous[0] != checksum:
                    raise ValueError(f"Applied migration changed: {path.name}")
                continue
            conn.execute(sql)
            conn.execute("INSERT INTO schema_migrations(version,checksum) VALUES (%s,%s)", (path.name, checksum))
            applied.append(path.name)
    return applied


def upsert_snapshot(snapshot, dsn=None):
    from psycopg.types.json import Jsonb
    from .normalize import normalize_job
    from .semantic import content_hash

    values = []
    for row in snapshot["records"]:
        normalized = normalize_job(row["raw_payload"], datetime.fromisoformat(row["fetched_at"]))
        if any(row.get(key) != value for key, value in normalized.to_record().items()):
            raise ValueError("Stored record differs from its source provenance")
        values.append((row["source"], row["source_id"], row["title"], row["company"], row["application_url"],
            normalized.salary_min, normalized.salary_max, row.get("currency"), row.get("salary_period"),
            Jsonb(row.get("location_restrictions")), Jsonb(row.get("timezone_restrictions")),
            row.get("source_updated_at"), row.get("expires_at"), row["fetched_at"], row["first_seen_at"],
            row["last_seen_at"], row.get("status_checked_at"), row["status"], row["is_active"], content_hash(row), Jsonb(row)))
    columns = ["source", "source_id", "title", "company", "application_url", "salary_min", "salary_max", "currency", "salary_period",
        "location_restrictions", "timezone_restrictions", "source_updated_at", "expires_at", "fetched_at", "first_seen_at", "last_seen_at",
        "status_checked_at", "status", "is_active", "content_hash", "record"]
    updates = [f"{column}=EXCLUDED.{column}" for column in columns if column not in {"source", "source_id", "first_seen_at", "record"}]
    updates.append("record=jsonb_set(EXCLUDED.record, '{first_seen_at}', jobs.record->'first_seen_at')")
    statement = f"INSERT INTO jobs ({','.join(columns)}) VALUES ({','.join(['%s']*len(columns))}) ON CONFLICT(source,source_id) DO UPDATE SET {','.join(updates)} WHERE EXCLUDED.fetched_at >= jobs.fetched_at"
    with connect(dsn) as conn:
        with conn.cursor() as cursor:
            cursor.executemany(statement, values)
        metadata = {key: value for key, value in snapshot.items() if key != "records"}
        conn.execute("INSERT INTO source_snapshots(source,metadata) VALUES (%s,%s) ON CONFLICT(source) DO UPDATE SET metadata=EXCLUDED.metadata", (snapshot["source"], Jsonb(metadata)))
        count = conn.execute("SELECT count(*) FROM jobs").fetchone()[0]
    return count


def read_snapshot(dsn=None):
    with connect(dsn) as conn:
        metadata = conn.execute("SELECT metadata FROM source_snapshots WHERE source='himalayas'").fetchone()
        if metadata is None:
            raise RuntimeError("Database has no ingestion snapshot")
        rows = conn.execute("SELECT record FROM jobs ORDER BY source, source_id").fetchall()
    return {**metadata[0], "records": [row[0] for row in rows]}


def save_vectors(entries, model, dsn=None):
    from .semantic import validate_vector
    values = [(row["source"], row["source_id"], model, row["content_hash"], json.dumps(validate_vector(row["vector"]))) for row in entries]
    with connect(dsn) as conn:
        with conn.cursor() as cursor:
            cursor.executemany("""INSERT INTO job_embeddings(source,source_id,model,content_hash,embedding)
                VALUES (%s,%s,%s,%s,%s::vector) ON CONFLICT(source,source_id,model)
                DO UPDATE SET content_hash=EXCLUDED.content_hash, embedding=EXCLUDED.embedding, created_at=now()""", values)


def vector_scores(records, vector, model, dsn=None):
    from psycopg.types.json import Jsonb
    from .semantic import content_hash, validate_vector
    allowed = [{"source": row["source"], "source_id": row["source_id"], "content_hash": content_hash(row)} for row in records]
    with connect(dsn) as conn:
        rows = conn.execute("""SELECT e.source, e.source_id, 1 - (e.embedding <=> %s::vector) AS similarity
            FROM job_embeddings e JOIN jsonb_to_recordset(%s::jsonb)
            AS allowed(source text, source_id text, content_hash text)
            ON e.source=allowed.source AND e.source_id=allowed.source_id AND e.content_hash=allowed.content_hash
            WHERE e.model=%s ORDER BY similarity DESC, e.source, e.source_id""",
            (json.dumps(validate_vector(vector)), Jsonb(allowed), model)).fetchall()
    return {(row[0], row[1]): row[2] for row in rows}
