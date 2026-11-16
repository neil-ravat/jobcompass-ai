# JobCompass

A working local job-recommendation backend using **real Himalayas listings**.
It combines FastAPI, explicit eligibility filters, explainable ranking,
PostgreSQL/pgvector, and local MiniLM semantic retrieval. An optional OpenAI tool
interprets natural-language queries; Python still enforces constraints.

**Ready for independent local review:** the final stabilization pass reproduced
136 passing tests, including four real PostgreSQL tests, in both the existing
environment and a clean installation. A fresh database, pgvector and downloaded
MiniLM model initialized successfully. The Docker images built and the local
Compose API passed health, jobs, recommendations and semantic-search checks.
The corpus still contains three real jobs; expansion awaits the daily refresh.
The optional LLM success path is **not live-verified** because no key is configured.
See the [final stabilization handoff](reports/FINAL_STABILIZATION.md) for exact
commands, results and limitations. No remote deployment is claimed.

## Open the running demo

- API docs: http://127.0.0.1:8765/docs
- Health/readiness: http://127.0.0.1:8765/health
- Local PostgreSQL: localhost:55432, database `jobcompass`.

The native demo and refresh worker were started during verification. For a new
terminal/session, the commands below reproduce the setup. Run one refresh worker
per data directory; concurrent ingestion writers are not supported.

## Install and run without PostgreSQL

Python 3.14.2 was used for verification; the project declares Python >=3.11.

```bash
cd /Users/neil/Documents/ChatGPT/jobcompass
uv sync --locked --all-extras
unset DATABASE_URL
bash scripts/demo.sh
```

The launcher performs one real ingestion/status refresh, builds or reuses local
embeddings, then runs the API and a five-minute refresh worker. First-time semantic
setup downloads the MiniLM ONNX weights. Later inference runs locally. Ctrl+C in
the launcher terminal stops the API and its worker.

The first captured feed contains three jobs. The normal refresh configuration is
20 jobs on one page; it takes effect at the next daily feed refresh, no earlier
than **18 November 2026, 02:54:55 IST** for the verified cache. Output always
reports the actual cached scope. No sample or fabricated job records are loaded.
Do not delete or change cache timestamps to force an early refresh. The worker
must remain running for a later refresh to happen automatically.

## Run with PostgreSQL

This machine already has PostgreSQL 16.14 and pgvector 0.8.2 installed, an isolated
cluster at `data/postgres`, and application/test databases. To reuse it:

```bash
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"  # this Mac's PostgreSQL binaries
pg_ctl -D data/postgres status || pg_ctl -D data/postgres -l data/postgres.log -o "-h 127.0.0.1 -p 55432 -k /tmp" start
export DATABASE_URL=postgresql://jobcompass@127.0.0.1:55432/jobcompass
.venv/bin/python -m jobcompass.manage migrate
bash scripts/demo.sh
```

For a fresh native installation with PostgreSQL 16 and pgvector available, initialize
only a **new** project cluster and create the databases:

```bash
mkdir -p data
initdb -D data/postgres --username=jobcompass --auth-local=trust --auth-host=trust --encoding=UTF8 --locale=C
pg_ctl -D data/postgres -l data/postgres.log -o "-h 127.0.0.1 -p 55432 -k /tmp" start
createdb -h 127.0.0.1 -p 55432 -U jobcompass jobcompass
createdb -h 127.0.0.1 -p 55432 -U jobcompass jobcompass_test
```

The native cluster uses loopback-only development trust authentication. The container
configuration below uses a password. To stop the native database later:
`pg_ctl -D data/postgres stop`.

`migrate` applies transactional, checksum-verified SQL migrations. With DATABASE_URL
set, ingestion upserts PostgreSQL and API reads use PostgreSQL. Connection failures
are explicit; they do not silently switch the API to JSON.

## Try the endpoints

```bash
curl 'http://127.0.0.1:8765/jobs?limit=1&offset=0'
curl 'http://127.0.0.1:8765/recommendations?q=engineer&country=ES'
curl 'http://127.0.0.1:8765/search?q=frontend%20web%20developer&country=ES'
```

| Endpoint | Behavior |
| --- | --- |
| GET /health | Liveness and data readiness; exposes no credentials. |
| GET /jobs | Hard constraints, all keyword tokens, stable pagination. |
| GET /recommendations | Hard constraints, at least one keyword match, lexical scores. |
| GET /search | Hard constraints, semantic retrieval and hybrid scores; q required. |
| POST /agent/query | Optional LLM intent extraction followed by the same Python search. |

Search parameters: `q`, `role`, `country`, `remote_only`, `min_salary`, `currency`,
`salary_period`, `limit` (1–100), and `offset`. Country accepts ISO codes or recognized
names. Currency uses ISO codes; pay periods are hourly, weekly, fortnightly,
monthly or annual. A salary floor requires currency and period.

Rules:

- Unknown country eligibility is excluded when a country is requested. Empty
  source restrictions mean unrestricted; missing restrictions mean unknown.
- Country checks do not determine work authorization or timezone compatibility.
  Those source restrictions remain visible. Remote means advertised as remote by
  the source, not that there are no location or travel requirements.
- Role tokens must occur in the title. Salary minimums must be known and meet the
  requested floor in matching units; no FX conversion or inferred offer is used.
- Lexical score: 60 title + 30 description + 10 categories, scaled by the fraction
  of query tokens matched in each field. Hybrid score: 70 × positive cosine
  similarity + 0.3 × lexical score. These scores are not hiring probabilities.
- Equal scores are ordered by source update time, then source identity. Rank
  pagination preserves this ordering.

Responses include original application URLs, source attribution, score components,
country eligibility and freshness. Invalid requests return 422; genuine empty
matches return 200 with an empty list; unavailable/stale data returns 503.

## Optional LLM workflow

Set OPENAI_API_KEY in your local environment and, optionally, OPENAI_MODEL (default
`gpt-5.4-mini`). No credentials are needed for the core API or local embeddings.
The application does not automatically load .env; export variables yourself.

```bash
curl -X POST http://127.0.0.1:8765/agent/query \
  -H 'Content-Type: application/json' \
  -d '{"message":"Find frontend web developer jobs","constraints":{"country":"ES"},"mode":"hybrid"}'
```

The model receives the query and supplied constraints, not the job corpus. One
strict `search_jobs` tool call is validated; explicit user constraints are applied
again before searching. The response shows `interpreted_query` and source-grounded
results. Without a key, this endpoint returns 503 `llm_unavailable`; malformed
provider tool output returns 502. A successful live provider call and extraction
quality remain unverified. [Official function-calling documentation](https://developers.openai.com/api/docs/guides/function-calling)

## Tests and measured evaluation

```bash
.venv/bin/python -m pytest -q
TEST_DATABASE_URL=postgresql://jobcompass@127.0.0.1:55432/jobcompass_test .venv/bin/python -m pytest -q
.venv/bin/python -m jobcompass.evaluate --k 1
.venv/bin/python -m jobcompass.evaluate --k 3
```

Without TEST_DATABASE_URL, four database tests skip. With the isolated database:
**136 passed** in both final verification environments (0.54s existing, 3.32s
clean). These are observed test durations, not application performance benchmarks.
One upstream Starlette/httpx deprecation warning remains. Database
tests require a database name ending in `_test` and clear only their test tables.
Source and LLM traffic is mocked in tests; separate live checks are documented in
[the final handoff](reports/FINAL_STABILIZATION.md).

`evaluations/real_jobs.json` contains Codex-assigned relevance judgments over three
real listings: three positive queries and one country-ineligible query. Labels
are **not independently human-reviewed**. Corpus fingerprints prevent silently
reusing labels after the job text changes. Evaluation uses the recorded snapshot
check time and averages relevance metrics only over queries with positive labels.

| Ranking mode | Precision@1 | NDCG@1 | Precision@3 | NDCG@3 |
| --- | --- | --- | --- | --- |
| Deterministic | 1.000 | 1.000 | 0.333 | 1.000 |
| Hybrid | 1.000 | 1.000 | 0.333 | 1.000 |

Both modes returned no jobs for the negative India case. Precision uses k as its
denominator even with fewer returned records. This tiny, deliberately labeled
sample is a sanity check, **not a production-quality benchmark or evidence that
semantic retrieval outperforms lexical ranking**. Outputs are in
`data/evaluation-k1.json` and `data/evaluation-k3.json`.

## Data freshness and source use

The feed is cached for 24 hours; individual status checks for ten minutes. The
worker wakes every five minutes and reuses these caches. Expiry is checked every
run. Long Retry-After delays extend the worker's sleep. Missing jobs are retired
only after a complete, valid traversal. Partial runs and failed refreshes cannot
mass-close stored records. Runtime snapshots, model weights, and database files
are ignored by Git.

Every display must visibly credit/link to Himalayas and every Apply action must
retain the supplied application URL. Do not redistribute source records to other
boards, aggregators or JobPosting feeds. [API documentation](https://himalayas.app/docs/remote-jobs-api),
[API terms](https://himalayas.app/terms). Greenhouse and Adzuna are deferred.

## Architecture and model

```text
Himalayas APIs → validation/normalization → JSON + optional PostgreSQL
                                           ↓
                           MiniLM embeddings → local index / pgvector
                                           ↓
FastAPI → hard constraints → lexical or hybrid ranking → grounded results
          ↑
optional LLM intent parser (validated tool arguments)
```

Model: `sentence-transformers/all-MiniLM-L6-v2`, FastEmbed/ONNX, 384 dimensions,
English, Apache-2.0, 256-token truncation. FastEmbed uses the
`Qdrant/all-MiniLM-L6-v2-onnx` artifact. Title and categories come before truncated
long descriptions. Model identity and document hashes guard index compatibility.
Weights used in verification had SHA256:
`bbd7b466f6d58e646fdc2bd5fd67b2f5e93c0b687011bd4548c420f7bd46f0c5`.
[Model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).

PostgreSQL stores typed normalized fields and raw provenance. pgvector uses exact
cosine search over already eligible IDs. There is no approximate index or ORM.
Read [the interview walkthrough](docs/INTERVIEW.md) for function-level explanations.

## Container configuration

The existing Dockerfile and compose.yaml were built and run locally during final
stabilization. Verification used an isolated Compose project, a new database
volume, and a temporary override mapping the API to localhost:8766 to avoid the
native demo on :8765. All four core endpoints passed. The temporary stack was
then removed; no remote deployment is claimed. Tested container versions were
Python 3.14.10, PostgreSQL 16.16 and pgvector 0.8.7. Base image tags can change.

For a container run, start Docker Desktop/the Docker daemon, stop the native demo
and its worker first, set a URL-safe POSTGRES_PASSWORD in the environment or
ignored .env, then:

```bash
docker compose build
docker compose up -d db
docker compose run --rm api python -m jobcompass.manage migrate
docker compose run --rm api python -m jobcompass.worker --once --semantic
docker compose up -d api refresh
curl -fsS http://127.0.0.1:8765/health
```

Use `docker compose down` to stop the container demo; its database volume is
retained. The clean verification reused the existing genuine job cache to respect
source refresh limits. Native verification downloaded fresh model weights;
container verification reused those weights and ran real query inference.

## Remaining limits

Only three live records were used for verification. The next daily refresh uses
the worker's configured 20-job page. Full-feed scale, broader relevance judgments,
LLM inference quality and production deployment are unverified. This is a local,
single-writer MVP without application authentication, distributed scheduling,
resume uploads or job-application automation. Do not expose it publicly without a
separate deployment review.

Milestone reports: [M1](MILESTONE_1_REPORT.md), [P1](reports/PHASE_1.md),
[P2](reports/PHASE_2.md), [P3](reports/PHASE_3.md), [P4](reports/PHASE_4.md),
[final stabilization](reports/FINAL_STABILIZATION.md).
All implementation code was generated by Codex under the user's direction.
