# JobCompass

Milestone 1 is implemented: a small Python backend ingests real Himalayas jobs,
normalizes them, checks their status, and saves a local snapshot. No application
records are fabricated; synthetic responses exist only in offline tests.

On 17 November 2026 the user asked Codex to implement one milestone at a time,
with explanations to follow. See [the plan](IMPLEMENTATION_PLAN.md) and the
[Milestone 1 report for ChatGPT](MILESTONE_1_REPORT.md).

## Run

From this directory:

```bash
uv sync --locked
.venv/bin/python -m pytest -q
.venv/bin/python -m jobcompass --limit 3 --max-pages 1
```

Without flags, the CLI requests up to 20 jobs on one page. `--max-pages` caps
pagination, and `--data-dir` chooses the output directory (default: `data/`).
Use a single process and the same directory so routine runs share the cache.

No key is required for this initial integration. An optional `HIMALAYAS_API_KEY`
environment variable enables server-side authentication. Never commit keys or
put them in URLs. Ignored `.env` files are not loaded automatically.
[Himalayas API reference](https://himalayas.app/docs/remote-jobs-api)

## Output and freshness

- `data/himalayas-feed.json`: real raw feed, fetch time, and effective page scope.
- `data/jobs.json`: normalized records, source credit, counts, diagnostics,
  source identity, original application links, and UTC status timestamps.
- The original Day 1 response and headers remain separate inspection evidence;
  the application never loads them as fixtures or fallback data.

The whole `data/` folder is ignored by Git. Feed requests reuse their cache for
24 hours. Page flags apply at the next feed refresh; output reports the effective
cached scope. Per-job status is checked again after ten minutes. Expiry is
checked on every run. [Refresh documentation](https://himalayas.app/docs/remote-jobs-api)

`is_active` describes status at the recorded check time, not a permanent
promise. Run ingestion before consuming an old snapshot. A future UI must check
freshness rather than display old JSON blindly. Closed/expired records remain
in local history as inactive; unknown status is also withheld from active results.
A partial feed never causes missing records to be marked closed.

```bash
.venv/bin/python -m json.tool data/jobs.json
```

Exit codes: `0` successful run, `1` failed run, `2` saved result with rejected
records or unsuccessful status checks. Failed refreshes preserve the previous
snapshot without reporting it as fresh. If the source requests a long delay,
the run stops; wait for that delay before retrying.

## Code map

```text
jobcompass/
  __main__.py       CLI, counts, exit codes
  himalayas.py      HTTP, bounded retries, cursors, per-job status
  models.py         typed Job dataclass and JSON conversion
  normalize.py      pure record validation and normalization
  ingest.py         caching, deduplication, status checks, atomic local upserts
tests/              offline contract and failure checks
```

Flow: CLI → feed → normalize → deduplicate → verify status → save.
No web server, database service, or scheduler is needed for this milestone.

## Storage contract

Identity is `(source, source_id)`. Himalayas `guid` and `applicationLink` are
preserved, including URL query parameters. Upserts retain `first_seen_at`.
Cross-source fuzzy deduplication is deferred.

Missing optional values stay unknown. Empty restriction arrays remain distinct
from missing fields. Locations become objects with a name and optional country
code; timezones become numeric UTC offsets. Both observed and documented schema
variants are supported. Salaries use Decimal in Python and exact decimal strings
in JSON; currency and pay period remain separate. Datetimes are UTC-aware and
serialize to ISO 8601. Invalid optional fields produce validation diagnostics;
invalid required fields reject the record. Raw source payloads are retained.

For later PostgreSQL storage: use a composite unique key on source/ID, NUMERIC
for salaries, TIMESTAMPTZ for dates, and JSONB for restrictions, diagnostics,
and raw payload. PostgreSQL is not connected in this milestone.

## Source use

Credit and link to Himalayas visibly, and use each original application URL for
Apply actions. Do not redistribute their jobs to third-party boards, aggregators,
or JobPosting feeds. [API terms](https://himalayas.app/terms)

Greenhouse is the planned secondary source, subject to board-specific reuse
checks. Adzuna remains optional pending credentials and permission. Neither is
implemented yet. No website scraping is used.
