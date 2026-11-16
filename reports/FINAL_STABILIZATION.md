# Milestone Handoff Report — JobCompass S1

**Milestone:** S1 — Final local MVP verification and stabilization  
**Date:** 17 November 2026, Asia/Kolkata  
**Decision:** Ready for independent local review, with the limitations below retained.

The bounded verification pass passed without an application-code change. Corpus
expansion is still pending the next permitted daily refresh. No external push or
remote deployment occurred. No additional feature milestone is starting.

## 1. Planned milestone requirements

| Requirement | Observed result |
| --- | --- |
| Reproduce the 136-test baseline | Passed in existing and clean environments, including four real PostgreSQL tests |
| Clean local API/PostgreSQL/pgvector/model setup | Passed with a new virtual environment, empty database cluster and fresh model download |
| Build/run existing Docker Compose and check four core endpoints | Passed locally; temporary port override prevented a collision with the native demo |
| Expand real corpus at the next permitted refresh | Pending: the existing feed is less than 24 hours old; no forced refresh |
| Repeat deterministic and hybrid evaluation | Passed on the same three-job corpus; all Codex relevance judgments remain UNREVIEWED |
| Check Git exclusions | Credentials, canonical runtime/data/model paths and caches are ignored; none tracked |
| Preserve optional LLM missing-key behavior | Native and container endpoints returned the expected safe 503 |
| Fix only demonstrated bugs; stop architecture expansion | No application defect demonstrated by this pass; documentation/status updates only |

## 2. Implemented features and behavior verified

Existing real-data ingestion, normalization, source identity, original application
URLs, visible Himalayas attribution, expiry/status filtering, deterministic ranking,
PostgreSQL persistence and local semantic retrieval remain intact. Both a clean
native installation and the container stack returned actual stored jobs.

The existing native API and refresh worker remain running on localhost:8765.
The temporary native API/database and the temporary Compose containers, network
and database volume were stopped/removed after verification. Temporary container
credentials were removed. Built images remain local.

## 3. Files created or modified

Repository: `/Users/neil/Documents/ChatGPT/jobcompass`.

| File | Change |
| --- | --- |
| `reports/FINAL_STABILIZATION.md` | This handoff, commands, evidence and limitations |
| `README.md` | Verified setup/container status, database restart instruction, exact next refresh time and demo steps |
| `IMPLEMENTATION_PLAN.md` | S1 outcome and stop on further feature progression |
| `AGENTS.md` | Persist the final directive: independent review next; no automatic feature milestone |

No Python source, test, SQL migration, dependency lock, Dockerfile or Compose
configuration changed. A temporary Compose override changed only the host API port.
Local evidence is deliberately ignored by Git at
`/Users/neil/Documents/ChatGPT/jobcompass/data/evidence/stabilization/`:

- `baseline-tests.txt`, `clean-tests.txt`, `clean-install.txt`, `clean-initdb.txt`.
- `api-smoke.json`, `clean-database.json`, `git-and-corpus.json`.
- `evaluation-k1.json`, `evaluation-k3.json` and corresponding terminal `.txt` logs.
- `verified-jobs.json`, `verified-himalayas-feed.json`: captured real evidence, not application seed files.
- `docker-build.txt`, `docker-run.txt`, `docker-database.txt`, `docker-api.json`, `docker-cleanup.txt`.

## 4. Important functions, endpoints and database changes

No schema or API changes were made. Verification exercised:

- `worker.refresh_once`: cache reuse, real snapshot persistence, embedding reuse/build.
- `database.migrate`, `upsert_snapshot`, `save_vectors`, `vector_scores`: fresh migration, three source-provenance rows, three 384-dimensional vectors and exact cosine retrieval.
- `semantic.embedding_model`, `embed_texts`, `recommend_semantic`: downloaded MiniLM initialization, local inference and hybrid ranking after hard filters.
- `evaluate.evaluate`: fingerprinted real corpus, explicit relevance grades and separate negative-query correctness.
- `GET /health`, `/jobs`, `/recommendations`, `/search`; `POST /agent/query` for safe missing-key behavior.

Existing tables remain `jobs`, `source_snapshots`, `job_embeddings` and
`schema_migrations`. Migration `001_jobs_and_vectors.sql` applied successfully to
the fresh native and container databases. A second native migration returned
`{"applied": []}`.

## 5. Tests executed, exact commands and actual results

### Full test suite

Existing workspace:

```bash
cd /Users/neil/Documents/ChatGPT/jobcompass
TEST_DATABASE_URL=postgresql://jobcompass@127.0.0.1:55432/jobcompass_test .venv/bin/python -m pytest -q
```

Actual terminal result:

```text
........................................................................ [ 52%]
................................................................         [100%]
136 passed, 1 warning in 0.54s
```

Clean tracked-file copy with no pre-existing virtual environment:

```bash
cd /private/tmp/jobcompass-stabilization-pm283pyt
uv sync --locked --all-extras
TEST_DATABASE_URL=postgresql://jobcompass@127.0.0.1:55433/jobcompass_test .venv/bin/python -m pytest -q
```

Actual install/test terminal results:

```text
Using CPython 3.14.2
Creating virtual environment at: .venv
Resolved 49 packages in 1ms
Prepared 44 packages in 5.84s
Installed 44 packages in 50ms
........................................................................ [ 52%]
................................................................         [100%]
136 passed, 1 warning in 3.32s
```

Both runs include four real database tests and zero skips. Both report the same
upstream warning:

```text
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

These timings are test-run observations, not application performance benchmarks.
Tests mock source/LLM HTTP traffic; the separate API and SQL checks below use real
captured source data and actual running services. The test suite was not run inside
the production Docker image, which intentionally omits development dependencies.

### Clean native setup and vector verification

Used existing installed PostgreSQL/pgvector binaries, with a **new empty cluster**:

```bash
cd /private/tmp/jobcompass-stabilization-pm283pyt
export PATH=/opt/homebrew/opt/postgresql@16/bin:$PATH
initdb -D data/postgres --username=jobcompass --auth-local=trust --auth-host=trust --encoding=UTF8 --locale=C
pg_ctl -D data/postgres -l data/postgres.log -o '-h 127.0.0.1 -p 55433 -k /private/tmp/jobcompass-stabilization-pm283pyt/data/postgres' start
createdb -h 127.0.0.1 -p 55433 -U jobcompass jobcompass
createdb -h 127.0.0.1 -p 55433 -U jobcompass jobcompass_test
export DATABASE_URL=postgresql://jobcompass@127.0.0.1:55433/jobcompass
.venv/bin/python -m jobcompass.manage migrate
.venv/bin/python -m jobcompass.manage migrate
JOBCOMPASS_PORT=8766 bash scripts/demo.sh
```

The genuine `jobs.json` and `himalayas-feed.json` were copied into the temporary
data directory before launch to preserve source cache times. No fabricated jobs,
time changes or forced feed request were used. The model cache started empty.

Observed results:

```text
server started
{"applied": ["001_jobs_and_vectors.sql"]}
{"applied": []}
```

The first worker run reported `feed_cache_used: true`, `degraded: false`,
`index.reused: false`, `indexed: 3`, `dimensions: 384`; its next run reused the
index. Native database queries reported PostgreSQL `16.14 (Homebrew)`, pgvector
`0.8.2`, three active jobs, three vectors, dimensions 384 and zero content-hash
mismatches. The fresh MiniLM ONNX artifact SHA256 was:

```text
bbd7b466f6d58e646fdc2bd5fd67b2f5e93c0b687011bd4548c420f7bd46f0c5
```

For `frontend web developer`, `database.vector_scores` returned InterNations
first with SQL cosine similarity `0.5112468600273132`. Comparing all three SQL
scores with Python cosine calculations gave maximum absolute difference
`1.3710110213782656e-08`.

This verifies a fresh Python environment, database cluster and model download;
it does not claim an operating-system reinstall or a new build of PostgreSQL itself.

### Successful API examples

The following checks passed against both native APIs and the container API:

| Request | Actual result |
| --- | --- |
| `GET /health` | 200, `ready: true`, `storage: postgresql`, `stored_jobs: 3` |
| `GET /jobs?limit=1` (native also tested offset=1) | 200, total 3, original source/application URLs and attribution |
| `GET /recommendations?q=engineer&country=ES` | 200, one InterNations Senior Full-Stack Engineer, lexical score 100 |
| `GET /search?q=frontend%20web%20developer&country=ES` | 200, same eligible job, cosine rounded to 0.511247 |
| `GET /search?q=web%20developer&country=IN` | 200, total 0 |
| `POST /agent/query` with a valid message and no key | 503, `code: llm_unavailable`; core endpoints remain available |

Native salary request without currency/period returned 422. Both native OpenAPI
descriptions contained the visible Himalayas link. Native hybrid score was
`40.78728`; container score was `40.787288` for the same result. This small numerical
variation across inference runtimes did not change ranking; bit-identical scores
across platforms are not claimed.

Actual health response, also confirmed after temporary-stack cleanup:

```json
{"status":"ok","ready":true,"storage":"postgresql","stored_jobs":3}
```

Actual missing-key response:

```json
{"detail":"OPENAI_API_KEY is not configured. /recommendations and /search work without an LLM.","code":"llm_unavailable"}
```

### Docker build and run

Initially the daemon was unavailable and the first build exited 1 with:

```text
Cannot connect to the Docker daemon at unix:///Users/neil/.docker/run/docker.sock. Is the docker daemon running?
```

After a bounded `docker desktop start --timeout 30`, `docker info` reported
`29.2.0`. The second build and complete local runtime checks succeeded. Compose
version was `v5.0.2`. Verification used the existing Dockerfile/compose.yaml with
only this temporary port override:

```yaml
services:
  api:
    ports: !override
      - "127.0.0.1:8766:8000"
```

A random URL-safe password was held in a temporary ignored `.env`, never printed.
Commands, run in the temporary tracked-file copy:

```bash
dc() { docker compose -p jobcompass-stabilization -f compose.yaml -f compose.verify.yaml "$@"; }
dc build
dc up -d db
dc run --rm api python -m jobcompass.manage migrate
dc run --rm api python -m jobcompass.worker --once --semantic
dc up -d api refresh
dc ps
dc exec -T db psql -U jobcompass -d jobcompass -c "SHOW server_version; SELECT extversion FROM pg_extension WHERE extname='vector'; SELECT count(*) AS jobs FROM jobs; SELECT count(*) AS embeddings,min(vector_dims(embedding)) AS dimensions FROM job_embeddings;"
dc exec -T api python --version
dc logs --no-color --tail 12 refresh
# After the successful HTTP checks:
dc down --volumes
```

Actual build terminal completion:

```text
Image jobcompass-stabilization-api Built
Image jobcompass-stabilization-refresh Built
```

All three services started; the database was healthy. Container SQL/runtime
results were PostgreSQL `16.16 (Debian 16.16-1.pgdg12+1)`, pgvector `0.8.7`,
three jobs, three 384-dimensional embeddings and Python `3.14.10`.
The refresh service reported cached feed/index reuse and `degraded: false`.
Container `/search` performed real local model inference using the downloaded
weights. No unresolved Docker blocker remains for this tested local run.

### Corpus, refresh eligibility and repeated evaluation

Actual corpus: **3 stored, 3 active**, 0 rejected, duplicates, expired, closed or
unverified; one cached three-job page, `feed_complete: false`. This is a partial
feed, not Himalayas' full corpus.

Feed captured: `2026-11-16T21:24:54.988908+00:00`. The next refresh allowed by the
application's 24-hour policy is `2026-11-17T21:24:54.988908+00:00`, or **18 November
2026 at 02:54:54.988908 IST**. The bounded pass finished before that time, so corpus
expansion was not performed. The existing worker defaults to 20 jobs/one page at
the next eligible refresh, if it remains running. No future successful refresh is
claimed. The daily-feed/ten-minute-status policy and source attribution follow
the [Himalayas API documentation](https://himalayas.app/docs/remote-jobs-api).

Exact evaluation commands, run against the existing real PostgreSQL index:

```bash
cd /Users/neil/Documents/ChatGPT/jobcompass
DATABASE_URL=postgresql://jobcompass@127.0.0.1:55432/jobcompass .venv/bin/python -m jobcompass.evaluate --k 1
DATABASE_URL=postgresql://jobcompass@127.0.0.1:55432/jobcompass .venv/bin/python -m jobcompass.evaluate --k 3
```

Both commands exited 0. Snapshot-as-of was `2026-11-16T22:45:06.676677+00:00`.

| Mode | Precision@1 | NDCG@1 | Precision@3 | NDCG@3 | Negative case |
| --- | --- | --- | --- | --- | --- |
| Deterministic | 1.0 | 1.0 | 0.3333333333333333 | 1.0 | Correct empty result |
| Hybrid | 1.0 | 1.0 | 0.3333333333333333 | 1.0 | Correct empty result |

**All relevance judgments were authored by Codex and remain UNREVIEWED by an
independent human.** There are three positive queries and one country-negative
query. Macro scores include only positive queries; precision divides by k even
when fewer results are returned. Evaluation uses the captured snapshot time,
not a claim that historical results remain fresh. These results provide a tiny
sanity check, not general quality evidence or evidence of hybrid superiority.

### Git status and exclusions

Latest implementation commit remains:
`ecbb08ee860c8b89621fe2eea032e1b3fa89115a` —
`feat: add evaluated local demo and reliable refresh delivery`.
Starting HEAD was documentation commit `1091b1c0d9c02c3c2b3b5fd2882cffb91d71d3c4`.
This stabilization checkpoint changes only the four documentation files above.

`git status --short` was empty at entry. `git diff --check` passed. A local
documentation commit records this handoff; final status is checked after commit.
No push was performed.

`git check-ignore` confirmed all ten probes: `.env`, `.env.local`, `.env.production`,
`data/jobs.json`, `data/postgres/PG_VERSION`, `data/models/weights.onnx`,
`data/embeddings.json`, `.venv/bin/python`, Python bytecode and pytest cache.
`.env.example` is intentionally tracked and contains no credential value.
The 47-file tracked inventory at entry contained zero forbidden runtime paths.
A limited scan for common private-key/AWS/OpenAI credential patterns found zero
matching files; this is not a comprehensive secret audit of Git history.

## 6. Bugs, incomplete features and known limitations

- No application bug was demonstrated by this pass. The upstream test-client
  deprecation warning remains; dependencies were not churned to suppress it.
- Corpus expansion is pending the permitted refresh time, not complete. Feed
  coverage remains partial and all relevance judgments remain unreviewed.
- Successful live LLM extraction/provider behavior is unverified; no API key
  was requested or required. Tests cover mocked success and failure cases.
- Container runtime checks passed locally; no external deployment, production
  reliability, broad relevance quality, load testing or full-feed scale is claimed.
- Base container tags can change. The observed versions above identify this run.
- One refresh writer per data directory is supported. Native/Compose production
  demo workers must not simultaneously write the same directory. Temporary
  verification used separate data directories and has been stopped.
- Model limitations, country versus work-authorization distinctions and unknown
  salary/eligibility handling remain as documented in README.md.

## 7. Architecture decisions and tradeoffs

Architecture was preserved. Fresh isolated environments tested setup without
changing the running demo. Genuine cached source data avoided needless API calls;
a fresh model download tested initialization. Exact pgvector cosine search remains
appropriate for this tiny corpus. Explicit unavailable responses remain preferable
to fabricated data or a hidden lexical fallback. Docker host-port override and a
temporary project name isolated verification without changing release configuration.

## 8. Independently implemented versus Codex-generated work

The user supplied requirements, scope decisions and manager directives. No
independently user-written Python solution was submitted during this pass. Existing
application/test code and this verification/documentation were generated or executed
by Codex. Do not describe the code as independently implemented by the user.

## 9. Concepts to understand for an interview

Explain source provenance and cache TTLs; missing versus unrestricted eligibility;
HTTP retries/Retry-After; atomic snapshots and idempotent database upserts; migrations
and transactions; hard filtering before ranking; cosine similarity and model/hash
compatibility; precision/NDCG and biased small-label evaluation; liveness versus
readiness; strict LLM tool validation and safe degradation; and why a local container
run does not demonstrate production deployment. Use docs/INTERVIEW.md and actual
tests to trace these behaviors.

## 10. Reproducible local demo instructions

On this already provisioned Mac, from a terminal with no duplicate demo worker:

```bash
cd /Users/neil/Documents/ChatGPT/jobcompass
uv sync --locked --all-extras
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
pg_ctl -D data/postgres status || pg_ctl -D data/postgres -l data/postgres.log -o "-h 127.0.0.1 -p 55432 -k /tmp" start
export DATABASE_URL=postgresql://jobcompass@127.0.0.1:55432/jobcompass
.venv/bin/python -m jobcompass.manage migrate
bash scripts/demo.sh
```

Then, in another terminal:

```bash
curl -fsS http://127.0.0.1:8765/health
curl -fsS 'http://127.0.0.1:8765/jobs?limit=1'
curl -fsS 'http://127.0.0.1:8765/recommendations?q=engineer&country=ES'
curl -fsS 'http://127.0.0.1:8765/search?q=frontend%20web%20developer&country=ES'
```

Open [local interactive API docs](http://127.0.0.1:8765/docs). The existing demo is
already running at handoff; use it directly instead of launching a second copy.
Results will change as real listings change. README.md includes fresh-cluster and
container setup. Ctrl+C stops a native demo and its worker. The core demo needs no
OpenAI key.

## 11. Exact next checkpoint and recommended task

**Next checkpoint: independent review of S1; no new feature milestone.** Reproduce
the four local endpoints and inspect the implementation/tests. At or after the
next permitted feed refresh, verify the actual corpus count, review relevance
labels independently and rerun the existing evaluation. The current fingerprint
guard intentionally rejects a changed corpus until labels are reviewed/updated.
Do not add features or seek an LLM key as a delivery prerequisite.

## Evidence Needed for Verification

- Independent reviewer reproduction of the native/Compose demo and test commands.
- Actual next eligible refresh output showing corpus growth, statuses, attribution
  and expiry handling; this pass does not supply that future evidence.
- Independently reviewed relevance grades on a broader real corpus and new metrics.
- A successful real LLM call only if that optional capability is later evaluated.
- Separate authorization and evidence before any remote deployment or push.

Local raw evidence is in the ignored stabilization directory listed above; it is
not included in a Git clone. The exact measured outcomes are preserved in this
committed handoff. Local MVP readiness is for independent review with these limits.
