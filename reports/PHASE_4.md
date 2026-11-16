# Milestone Handoff Report — JobCompass P4 / Local MVP Delivery

## 1. Project, milestone and status

**Project:** JobCompass
**Milestone:** P4 — Evaluation and delivery, consolidating P1–P3
**Date:** 17 November 2026, Asia/Kolkata
**Target:** Working, tested, interview-ready MVP by 23 November 2026
**Status:** The core local MVP is running and verified. Optional successful live
LLM inference and container/remote deployment remain unverified.

| Checkpoint | Status and actual evidence | Local implementation commit |
| --- | --- | --- |
| P1 API and deterministic recommendations | 97 tests; real filtered API response | 10b88d5 |
| P2 PostgreSQL and semantic retrieval | 110 tests; real SQL, three jobs and three vectors; live semantic response | 4efcacf |
| P3 LLM-assisted query | 126 tests; safe missing-key response; successful provider call blocked by absent key | f77c7ac |
| P4 evaluation and delivery | Final 136 tests; measured labeled evaluation; live demo checks | ecbb08e |

No Git push or remote deployment was performed. The repository is
`/Users/neil/Documents/ChatGPT/jobcompass`. Earlier M1 ingestion was preserved and
extended rather than rebuilt.

## 2. Planned milestone requirements

Add representative labeled cases and measured Precision@K/NDCG@K where labels
exist; test source failures, freshness and attribution; provide a reproducible
local demo and interview-ready guide; add deployment configuration where feasible;
record actual outcomes and limitations; create clean local Git checkpoints while
excluding secrets and runtime data.

## 3. Implemented features and demonstrably working behavior

- Local API at `http://127.0.0.1:8765`, interactive docs at `/docs`, and a running
  isolated PostgreSQL instance at localhost:55432.
- Real Himalayas ingestion, normalization, required/optional validation, cursor
  pagination, retries, source identity, original application links and status checks.
- `/health`, `/jobs`, `/recommendations`, `/search`, and optional `/agent/query`.
- Hard country/role/remote/salary constraints followed by deterministic or hybrid
  ranking with component scores. Missing country eligibility is never confirmed.
- Typed PostgreSQL persistence and transactional idempotent upserts; real pgvector
  cosine queries over hard-eligible records; local MiniLM inference.
- A single refresh worker reuses the daily feed cache, ten-minute status cache and
  unchanged embeddings. Long Retry-After delays extend its sleep.
- A launcher refreshes data/indexes, starts the worker and API, and cleans up its
  worker on exit. Startup and a later worker cycle were observed successfully.
- Explicitly labeled evaluation with fingerprinted real-job text. Changed corpus
  text invalidates labels instead of silently producing misleading metrics.
- Source credit is visible in API documentation and response metadata. Unknown or
  failed source status is not disguised as an ordinary successful empty result.

## 4. Exact files created or modified in P4

Created:

- `.dockerignore`, `.env.example`, `Dockerfile`, `compose.yaml`
- `docs/INTERVIEW.md`, `docs/MANAGER_DIRECTIVE.md`
- `evaluations/real_jobs.json`
- `jobcompass/evaluate.py`, `jobcompass/worker.py`
- `scripts/demo.sh`
- `tests/test_evaluate.py`, `tests/test_worker.py`

Modified:

- `.gitignore`, `IMPLEMENTATION_PLAN.md`, `README.md`
- `jobcompass/api.py`, `jobcompass/himalayas.py`, `jobcompass/search.py`,
  `jobcompass/store.py`
- `tests/test_agent.py`, `tests/test_api.py`, `tests/test_search.py`
- `reports/PHASE_3.md` (recorded its real implementation commit)

This handoff (`reports/PHASE_4.md`) is saved after the implementation checkpoint.
Runtime evidence, model weights and database files remain ignored under `data/`.
`git ls-files -- data .env .venv` returned no tracked runtime/secret files.

## 5. Important functions, classes, APIs and database changes

P4 functions: `precision_at_k()`, `ndcg_at_k()`, `evaluate()`,
`worker.refresh_once()`, `worker.retry_wait()`, and the worker CLI.
`RetryDeferred` now carries a delay for the refresh loop. `filter_jobs()` respects
explicit nonremote status and standalone currency/period constraints.
`load_snapshot()` rejects wholly unverified status; API pages expose partial
status/rejection counts.

Existing core: `Job`, `normalize_job()`, `fetch_page()`, `fetch_job()`, `ingest()`,
`SearchParams`, `rank_jobs()`, `recommend_semantic()`, `interpret_query()`.
Database operations: `migrate()`, `upsert_snapshot()`, `save_vectors()`,
`vector_scores()`. Tables: schema_migrations, jobs, source_snapshots,
job_embeddings with vector(384). P4 adds no further schema migration.

External APIs: official Himalayas browse/status APIs; optional OpenAI Responses
API for one validated `search_jobs` tool call. No source scraping or multi-agent
framework is used.

## 6. Commands executed and actual test/results evidence

### Automated regression

```bash
TEST_DATABASE_URL=postgresql://jobcompass@127.0.0.1:55432/jobcompass_test .venv/bin/python -m pytest -q --tb=short
```

Final observed result: **136 passed, 1 warning**. The warning is an upstream
Starlette/httpx test-client deprecation. Four tests use a real dedicated PostgreSQL
`*_test` database; source and LLM calls are mocked. Added final tests verify a
positive agent-to-retrieval response, explicit country locking, partial/all-status
failure behavior, nonremote overrides, metrics and worker cache/cooldown behavior.

### Measured relevance evaluation

```bash
.venv/bin/python -m jobcompass.evaluate --k 1
.venv/bin/python -m jobcompass.evaluate --k 3
```

Executed against the saved real snapshot and local vector index as of its recorded
check time. Three real listings, three positive queries and one negative country
query; **Codex-assigned labels, not independently human-reviewed**.

| Mode | Precision@1 | NDCG@1 | Precision@3 | NDCG@3 |
| --- | --- | --- | --- | --- |
| Deterministic | 1.000 | 1.000 | 0.333333 | 1.000 |
| Hybrid | 1.000 | 1.000 | 0.333333 | 1.000 |

Both modes correctly returned no records for the negative India query. Macro
relevance means cover only the three queries with positive labels; negative
queries are reported separately. Precision divides by K, even if fewer results
are returned. Results: `data/evaluation-k1.json`, `data/evaluation-k3.json`.

These are measured sanity checks on a tiny, easy, author-labeled corpus. They do
not establish production accuracy, unbiased recommendation quality, or a semantic
improvement over lexical ranking.

### Running local demonstration

```bash
DATABASE_URL=postgresql://jobcompass@127.0.0.1:55432/jobcompass bash scripts/demo.sh
```

Observed: three stored/active records, no rejected/unverified jobs, feed cache
reused, unchanged embeddings reused, PostgreSQL-backed server started on 8765.
The worker also completed a subsequent refresh cycle successfully.

Live HTTP checks, saved in `data/evidence/final-smoke.json`:

| Request | Actual result |
| --- | --- |
| GET /health | 200, ready=true, storage=postgresql |
| GET /jobs?limit=1&offset=1 | 200, pagination over three records |
| GET /recommendations?q=engineer&country=ES | 200, one real eligible result |
| GET /search?q=frontend%20web%20developer&country=ES | 200, one real hybrid result |
| GET /search?q=web%20developer&country=IN | 200, no eligible results |
| GET /jobs?min_salary=100 | 422, missing currency/pay-period validation |
| GET /docs | 200, Swagger HTML |
| POST /agent/query without credentials | 503, llm_unavailable |

OpenAPI metadata was also checked for visible Himalayas credit. The real semantic
example was InterNations' Senior Full-Stack Engineer with its original URL:
`https://himalayas.app/companies/internations/jobs/senior-full-stack-engineer?utm_source=api`.
Earlier SQL checks confirmed PostgreSQL 16.14, pgvector 0.8.2, three jobs and three
384-dimensional embeddings. A query produced cosine similarity 0.511247; this is
an observed similarity score, not a calibrated relevance probability.

### Configuration and repository checks

- `bash -n scripts/demo.sh`: passed.
- `POSTGRES_PASSWORD=validation-only-not-secret docker compose config --quiet`:
  passed; the placeholder was only for parsing, not an installed credential.
- `git diff --check` and staged checks: passed after removing Markdown trailing
  spaces from the copied directive.
- Clean implementation checkpoints were created locally; no push was executed.

## 7. Bugs fixed, blockers, incomplete and unverified work

Fixed during the project: cached expiry resurrection, UTC first-seen serialization
on upsert, ignored standalone currency/period filters, punctuation-only queries,
nonremote overrides and status failures appearing as empty success.

Remaining limits:

- **Exact LLM blocker:** OPENAI_API_KEY is not configured. Successful live provider
  inference, account/model access, extraction quality, cost and latency are unverified.
- Docker configuration passed parsing; the image was **not built**, containers were
  **not launched**, and no remote deployment was attempted.
- Three live jobs are a sample, not a complete feed. The next normal daily refresh
  uses the worker's 20-job page. Larger-corpus behavior and performance are unmeasured.
- Relevance labels need independent review and expansion. Current numbers cannot
  be treated as broad recommendation-quality claims.
- Single ingestion writer, local development authentication, no public API auth,
  no distributed scheduling, and no approximate vector index. Native PostgreSQL
  trust authentication is limited to the local development setup.
- Country eligibility does not determine visas or timezone compatibility. Salaries
  are only filtered when structured values and units are available.
- MiniLM truncates long input; package versions are locked and the used model
  checksum is documented, but future model downloads should be checked for drift.
- Greenhouse, Adzuna, elaborate frontend and application submission remain deferred.

## 8. Architecture decisions and tradeoffs

Keep the existing Python ingestion and JSON fallback. Add a read-only FastAPI layer,
explicit SQL/migrations and a small local embedding library. Apply hard constraints
before scoring; use exact vector search for the current small corpus. Use model
identity and document hashes to reject stale indexes. Treat the LLM as an intent
parser with strict schema/runtime validation and reapply explicit user constraints.
Return retrieved records directly. A single refresh process provides freshness
without queue infrastructure. Container files are optional delivery configuration,
not claimed deployment evidence.

## 9. Independently implemented versus Codex-generated work

The user defined requirements, sources, deadline, project-manager priorities and
handoff policy. No user-written Python was submitted in these milestones. Codex
generated code, tests, schema, configuration, relevance judgments, documentation
and reports, and executed the recorded verification. The user can study the
implementation using `docs/INTERVIEW.md`; authorship should not be misrepresented.

## 10. Interview concepts

HTTP/schema validation; null versus empty restrictions; Decimal and UTC; bounded
retries and Retry-After; opaque cursor pagination; source provenance; idempotent
upserts, transactions and unique keys; safe reconciliation; cache freshness;
embeddings, cosine distance and truncation; hard constraints versus ranking;
Precision@K/NDCG@K and label bias; strict function schemas versus trusted execution;
mock tests versus live integration evidence; and local versus production deployment.

## 11. Exact next milestone and recommended task

**Next checkpoint: P3-V — complete live LLM verification.** When a valid key is
available, execute one bounded `/agent/query` request with an explicit country
constraint and compare interpreted intent, returned source IDs and application
URLs. Do not claim success until that request actually completes.

Independent next task while credentials are unavailable: after the permitted daily
feed refresh, expand the real corpus, obtain independent relevance judgments, and
repeat the fingerprinted evaluation. Optional container build/run verification can
follow. No further feature milestone is automatically starting after this handoff.

## Evidence Needed for Verification

Available locally: all source/tests, four implementation commits, migrations,
`data/jobs.json`, `data/himalayas-feed.json`, the local PostgreSQL database,
`data/embeddings.json`, `data/evaluation-k1.json`, `data/evaluation-k3.json`, and
`data/evidence/phase1-api.json`, `phase2-api.json`, `phase3-api.json`,
`final-smoke.json`. Runtime data is deliberately excluded from Git.

An independent reviewer should rerun the database-enabled suite and recorded HTTP
requests, inspect the original URLs/status timestamps, and review the labels before
using the metrics. A separate ChatGPT conversation cannot read local files by path
alone; provide this report and relevant files/output for audit. Successful live
LLM, broader human-reviewed relevance, container execution and remote deployment
still require new evidence; none is fabricated or implied by configuration files.
