# Milestone Handoff Report

## 1. Project and milestone

- **Project:** JobCompass
- **Milestone ID:** M1 — Real Job Data Ingestion
- **Date:** 17 November 2026, Asia/Kolkata
- **Status:** Implemented and verified for a small live Himalayas sample, with
  offline tests for pagination and failure cases. A full-feed mirror was not run.
- **Repository:** `/Users/neil/Documents/ChatGPT/jobcompass`
- **Commits:** None. The repository has no commits; all project files are
  uncommitted. No commit hash, deployment, or database installation is claimed.

## 2. Planned requirements

Connect to the official Himalayas API; retrieve real published jobs; inspect and
validate JSON; normalize records; safely handle missing values; preserve source,
source ID, and application URL; detect duplicates; handle HTTP failures,
timeouts, and rate limits; and prepare records for later PostgreSQL storage.
Respect attribution, refresh limits, and expired/closed-job handling. Mock data
may exist only in tests. Complete one milestone before moving to the next.

## 3. Implemented features and behavior

- A runnable Python CLI fetches the real browse API and follows opaque cursors
  up to an explicit page cap. Results state whether the feed is complete.
- JSON envelope validation and record normalization distinguish invalid required
  fields from optional unknown values. Rejections and diagnostics are recorded.
- A typed `Job` dataclass preserves source identity, original application URL,
  raw source data, exact salary values, currency/period, and UTC dates.
- Both observed and documented location/timezone shapes are supported. Missing
  restrictions remain unknown rather than becoming worldwide eligibility.
- Source-identity deduplication and local upserts retain first-seen timestamps.
- Requests use finite timeouts, bounded retries, request pacing, and Retry-After
  handling. Long server-requested waits stop the run instead of being ignored.
- Feed caching lasts 24 hours. Per-job status is refreshed after ten minutes;
  expiry is checked each run. Closed, expired, and unverified jobs are inactive.
- Only a complete, valid feed can reconcile missing jobs. Partial/failed fetches
  do not mark all previous jobs closed. Failed refreshes preserve prior output.
- Atomic JSON snapshots include attribution, counts, diagnostics, status and
  freshness metadata. Runtime data is ignored by Git; no fabricated seeds exist.

## 4. Files created or modified

All paths below are relative to the repository. “Modified” refers to changes to
the earlier learning scaffold; Git still considers all files untracked.

| File | Change and purpose |
| --- | --- |
| `jobcompass/himalayas.py` | Modified: implemented HTTP, retries, page validation and status API. |
| `jobcompass/models.py` | Created: `Job` model and storage conversion. |
| `jobcompass/normalize.py` | Created: normalization and validation helpers. |
| `jobcompass/ingest.py` | Created: cache, pagination, deduplication, status and persistence. |
| `jobcompass/__main__.py` | Created: runnable CLI and exit-code handling. |
| `tests/test_himalayas.py` | Modified: request and retry contract tests. |
| `tests/conftest.py` | Created: offline guard and test-only fixtures. |
| `tests/test_normalize.py` | Created: normalization and malformed-value cases. |
| `tests/test_ingest.py` | Created: pipeline, caching, expiry and reconciliation cases. |
| `tests/test_cli.py` | Created: failed/degraded CLI outcomes. |
| `README.md` | Rewritten: setup, operation, freshness and storage contract. |
| `IMPLEMENTATION_PLAN.md` | Updated: revised authorization, M1 evidence, next milestones. |
| `AGENTS.md` | Created: persistent milestone/reporting requirements. |
| `MILESTONE_1_REPORT.md` | Created: this handoff. |

Existing scaffold retained: `pyproject.toml`, `uv.lock`, `.gitignore`, and
`jobcompass/__init__.py`. Generated real-data artifacts:
`data/himalayas-feed.json` and `data/jobs.json` (ignored by Git).

## 5. Important functions, APIs and database changes

- `himalayas.fetch_page()` — validated browse response and cursor handling.
- `himalayas.fetch_job()` — checks the official per-job endpoint and verifies
  response identity; 404/410 means absent/closed.
- `himalayas._request()` / `RetryDeferred` — bounded retries and long-delay exit.
- `normalize.normalize_job()` — pure mapping and field validation.
- `models.Job` / `Job.to_record()` — typed record and JSON-safe conversion.
- `ingest.ingest()` — complete ingestion orchestration and local upserts.
- `ingest._save()` — temporary-file write followed by atomic replacement.
- `__main__.main()` — CLI; exit 0 success, 1 failure, 2 degraded output.

Endpoints used:

```text
GET https://himalayas.app/jobs/api?limit=3
GET https://himalayas.app/jobs/api?limit=...&cursor=...
GET https://himalayas.app/jobs/api/companies/{company}/jobs/{slug}
```

No database changes were applied. PostgreSQL preparation consists of a stable
record contract: composite `(source, source_id)` identity, Decimal salaries for
NUMERIC, UTC datetimes for TIMESTAMPTZ, and JSON-compatible lists/raw data for
JSONB. There is no SQL migration, PostgreSQL connection, or ORM yet.

## 6. Verification executed and actual results

Environment: Python 3.14.2; dependencies were installed during scaffolding.

**Offline suite:**

```bash
.venv/bin/python -m pytest -q --tb=short
```

Actual final result: **74 passed**. Tests prevent Requests network access.
Coverage includes success, empty data, invalid JSON/schema, timeouts, transient
connections, 429/503, Retry-After seconds and HTTP-date, non-retryable auth errors,
cursor loops, source identity, normalization, duplicates, expiry, status cache,
safe reconciliation, preserved output on failure, and CLI error paths.

**Real integration run:**

```bash
.venv/bin/python -m jobcompass --limit 3 --max-pages 1
```

Actual result around 02:55 IST on 17 November: exit 0; 3 fetched, 3 accepted,
3 stored, 3 verified open, 0 rejected, 0 duplicates, 0 expired, and 0 status
errors. `feed_complete=false` correctly identified the capped sample.
No API credentials were needed for this run.

**Repeat/cache verification:** executed the same CLI from a Python subprocess,
then compared the before/after `data/jobs.json` records. Exit 0;
`feed_cache_used=true`; exactly 3 records remained; the records were identical,
including first-seen timestamps. Assertions confirmed every source ID matched
raw `guid` and every application URL matched raw `applicationLink`.

**Repository check:** `git status --short --untracked-files=all` showed uncommitted
files; `git log -1 --format='%h %s'` confirmed there are no commits.

## 7. Bugs, incomplete features and limitations

- Fixed during testing: a cached detail response with an earlier expiry could
  be replaced by an older feed record, incorrectly reactivating an expired job.
  The first run had 68 passes and this one failure; the regression now passes.
- No remaining failing tests were observed. This is not a claim of zero bugs.
- Live verification covers only three jobs. Pagination, rate limits and error
  conditions were exercised with mocks, not induced against the live provider.
- The CLI is intended for one process. It has atomic output writes but no
  cross-process locking, distributed cache, or scheduler.
- A long rate-limit delay requires waiting before rerunning; no background
  retry job or persistent cross-process cooldown is installed.
- Source status can change after a check. Old JSON must not be presented as
  permanently current. Page flags apply on the next feed refresh, not to a
  still-valid cached feed; the effective scope is reported.
- Greenhouse, Adzuna, PostgreSQL, filters, ranking, a web UI, and deployment are
  not implemented. Cross-source fuzzy deduplication is also deferred.

## 8. Architecture decisions and tradeoffs

- Synchronous Requests plus standard-library dataclasses keeps M1 small and
  readable. No framework, async worker, or database service is needed yet.
- HTTP, normalization, and orchestration are separate so failure behavior can
  be tested offline and future storage can replace local JSON.
- Local atomic snapshots provide a runnable persistence step; PostgreSQL is
  deferred rather than claiming database integration prematurely.
- Conservative status/expiry handling avoids presenting unknown jobs as open.
  Keeping inactive historical records preserves provenance and first-seen data.
- Raw payload retention supports debugging schema drift. Runtime output is
  excluded from Git and must not become a redistributed job feed.

## 9. Learner work versus Codex-generated work

- **User:** supplied requirements, selected sources and deadline, authorized the
  switch from independent exercises to Codex implementation, and defined this
  mandatory handoff format.
- **Independently implemented by the user:** no Python implementation was
  submitted in this milestone.
- **Codex:** generated the scaffold, implementation, tests, documentation and
  report; executed the offline tests and live/cache verification.

## 10. Interview concepts to understand

HTTP GET and status codes; JSON dictionaries/lists/null; finite timeouts;
transient versus permanent failures; bounded backoff and Retry-After; cursor
pagination; dataclasses and pure functions; required versus optional validation;
Decimal versus float for money; timezone-aware timestamps; idempotent upserts
and composite unique keys; cache freshness; source provenance; atomic writes;
unit mocks versus live integration tests; and why partial fetches cannot safely
reconcile missing records.

## 11. Exact next milestone and recommended task

**M2 — Job Filtering and Explainable Ranking.**

First recommended task: implement and test a `filter_jobs()` function over the
normalized records, starting with keyword and country eligibility. Explicitly
distinguish restricted, unrestricted, and unknown eligibility. Add deterministic
ranking and per-job score explanations after those filters work.

M2 has not been started. This handoff ends M1; no automatic advance occurs.
The overall MVP target remains 23 November 2026.

## Evidence Needed for Verification

- Available locally: implementation and tests, the real raw feed in
  `data/himalayas-feed.json`, and normalized/status evidence in `data/jobs.json`.
- For independent verification, rerun the documented pytest command and inspect
  `source_id`, `application_url`, `status_checked_at`, `feed_complete`, and counts
  in the snapshot. Re-run the CLI within the source refresh policy to check status.
- A separate ChatGPT conversation cannot inspect these local paths by itself;
  provide the report plus relevant source files or terminal output if it needs
  to audit the claims independently.
- Full-feed behavior at live scale, PostgreSQL persistence, Greenhouse/Adzuna,
  UI behavior and deployment need new evidence in their future milestones.
  No such evidence or commit hash exists for M1.
