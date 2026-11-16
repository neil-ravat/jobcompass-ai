# Milestone Handoff Report — JobCompass P2

## Project, status and planned requirements

17 November 2026. P2 — PostgreSQL and semantic retrieval — passed for the small
real corpus. Required: typed schema, migrations, idempotent upserts, preserved
status/provenance, documented embeddings, vector search, hard constraints and tests.

## Implemented features and behavior

PostgreSQL stores normalized fields plus original record provenance. Versioned,
checksum-verified migrations are transactional. Upserts preserve first-seen time.
MiniLM produces local 384-dimensional embeddings. pgvector performs exact cosine
queries only over hard-eligible records. Hybrid ranking combines 70 times positive
cosine similarity with 30% of the lexical score. Content hashes reject stale
embeddings. JSON-backed ingestion/API and a local vector index remain available
when DATABASE_URL is unset; configured database failures are not hidden by fallback.

## Files created or changed

Created: migrations/001_jobs_and_vectors.sql, jobcompass/database.py,
jobcompass/semantic.py, jobcompass/manage.py, tests/test_database.py,
tests/test_semantic.py, reports/PHASE_2.md.
Changed: jobcompass/search.py, jobcompass/store.py, jobcompass/api.py,
jobcompass/__main__.py, tests/test_api.py, pyproject.toml, uv.lock,
reports/PHASE_1.md. Model artifacts and database files are ignored under data/.

## Important functions, APIs and database changes

migrate(), upsert_snapshot(), read_snapshot(), save_vectors(), vector_scores();
build_index(), recommend_semantic(), hybrid_rank(); GET /search.
New tables: schema_migrations, jobs, source_snapshots, job_embeddings.
Composite source identity is unique; job_embeddings references jobs and stores
vector(384). There is no approximate index for this small corpus.
Model: sentence-transformers/all-MiniLM-L6-v2 via FastEmbed 0.9.1, ONNX CPU,
Apache-2.0, English, 256-token truncation. Model card:
https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
FastEmbed downloads Qdrant/all-MiniLM-L6-v2-onnx. Text stays on this machine.

## Commands executed and actual results

- `uv sync --all-extras --cache-dir /private/tmp/jobcompass-uv-cache`: installed
  psycopg, FastEmbed, ONNX Runtime and dependencies successfully on Python 3.14.2.
- Compiled pgvector v0.8.2 for installed PostgreSQL 16.14; installed extension.
- Initialized an isolated data/postgres cluster, listening only on localhost:55432.
  Created separate jobcompass and jobcompass_test databases.
- `DATABASE_URL=postgresql://jobcompass@127.0.0.1:55432/jobcompass .venv/bin/python -m jobcompass.manage migrate`:
  001_jobs_and_vectors.sql applied; reruns applied nothing.
- `... python -m jobcompass.manage sync`: 3 real jobs stored.
- `... python -m jobcompass --limit 3 --max-pages 1`: real status refresh plus
  PostgreSQL upsert succeeded, all three jobs open.
- `... python -m jobcompass.manage embed`: 3 embeddings, 384 dimensions, stored
  locally and in pgvector.
- `TEST_DATABASE_URL=postgresql://jobcompass@127.0.0.1:55432/jobcompass_test .venv/bin/python -m pytest -q --tb=short`:
  **110 passed**, including four real database tests. One upstream test-client
  deprecation warning remains.
- Live GET `/search?q=frontend%20web%20developer&country=ES`: returned the real
  InterNations Senior Full-Stack Engineer, original application URL preserved;
  cosine similarity 0.511247, score components semantic 35.78728 + lexical 5.
  This is one observed response, not a recommendation-quality benchmark.
- Actual SQL confirmed PostgreSQL 16.14, pgvector 0.8.2, 3 jobs and 3 vectors of
  dimension 384. Evidence response: data/evidence/phase2-api.json.

## Bugs, limitations and incomplete work

Fixed: ON CONFLICT previously reserialized first_seen_at using the database's
local timezone; the upsert now preserves the original UTC JSON representation.
Initial DB suite: 109 passed, one failed; final suite: 110 passed.
Only three real records were used; no scale/performance claim. Exact search and
in-memory hard filtering suit the MVP, not a large production feed. Model truncates
long descriptions. Migrations are forward-only. The isolated local cluster uses
trust authentication on loopback for development, not production configuration.
LLM workflow, evaluation and deployment packaging remain for later phases.

## Architecture decisions and tradeoffs

Parameterized SQL and explicit migrations avoid an ORM layer. PostgreSQL stores
queryable normalized fields and a full record for provenance. Local MiniLM avoids
paid embedding credentials and external job-data transmission. Exact pgvector
queries prioritize correctness and explainability over approximate-index scale.
Explicit model/content hashes prevent mixing incompatible or stale vectors.

## User versus Codex work and interview concepts

All code/tests/setup generated and executed by Codex. User supplied requirements;
no user-written implementation was submitted. Understand transactions, upserts,
unique/foreign keys, migrations, vector dimensions, cosine similarity, text
truncation, hard filters before retrieval, hybrid scores, and stale-index detection.

## Exact next milestone

P3 — Minimal LLM-assisted career query. Add a validated tool schema invoking the
existing recommendation functions. No LLM key is configured; test safe unavailable
and malformed-response behavior and report the live-call limitation honestly.

## Evidence Needed for Verification

Rerun the database-enabled suite against the dedicated *_test database. Inspect
migrations and data/evidence/phase2-api.json, then query counts/vector dimensions
in the local application database. The live result does not establish relevance
quality; labeled evaluation is P4. No remote deployment or push is claimed.
