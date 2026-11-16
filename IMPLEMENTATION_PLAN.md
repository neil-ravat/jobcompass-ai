# JobCompass — real-data implementation plan

Revised 17 November 2026 (Asia/Kolkata). Delivery target: 23 November 2026,
end of day. The workspace had no prior plan or application files; this records
the supplied requirements as the working plan.

## Working agreement

Every application listing must originate in a real permitted API response.
No fabricated seed records, hardcoded results, or mock-data fallback. If a source
fails, report the failure; an empty successful response is a different outcome.
Small synthetic responses are allowed only inside unit tests. Local inspection
captures stay untracked and are not permanent application fixtures.

Updated authorization, 17 November 2026: the user asked Codex to build one
milestone at a time because of the deadline, and to provide reports for a separate
ChatGPT Project Milestone Manager. This supersedes the earlier requirement that
the learner implement core functions independently. Codex implements and verifies
each milestone; the learner will study the implementation later.

After every completed or attempted major milestone, provide a Markdown handoff
covering requirements, implementation, files, functions/endpoints/database work,
actual verification, limitations, decisions, code authorship, interview concepts,
and the exact next milestone. End with **Evidence Needed for Verification**.
Do not advance to the next milestone before delivering the report. The latest manager directive permits autonomous progression after each reported checkpoint. Repository guidance in AGENTS.md preserves this workflow.

## Seven-day delivery sequence

| Day | Date | Outcome and acceptance evidence |
| --- | --- | --- |
| 1 | 17 Nov | **Milestone 1 complete:** real ingestion, normalization, retries, cursors, deduplication, expiry/status checks, local persistence, CLI, and verification. |
| 2–3 | 18–19 Nov | Milestone 2: location/keyword filters and deterministic ranking with explanations; tests for unknown eligibility and empty matches. |
| 4–5 | 20–21 Nov | Milestone 3: a small usable results interface connecting ingestion and matching, with attribution, freshness, and failure states. |
| 6 | 22 Nov | Timebox a secondary Greenhouse adapter for one permitted board after the primary workflow passes. |
| 7 | 23 Nov | Final regression tests, controlled live verification, documentation, and learner walkthrough. |

The required MVP uses Himalayas. If time is tight, move Greenhouse integration to
the next milestone while retaining it as the secondary source. Adzuna remains
optional and disabled until credentials and usage permissions are verified.
PostgreSQL deployment, a full web UI, accounts, embeddings, and background job
queues are outside this week's minimum. PostgreSQL-compatible records are ready;
the database itself is a later storage milestone if required.

## Sources and operating rules

**Himalayas — primary.** Use the documented browse API with cursor pagination,
at most 20 jobs per page. The first request needs no key. Refresh the feed no
more than daily; observe 429 and `Retry-After`. Public callers share an allowance;
do not assume a dedicated public quota. A page cap makes a run partial, even if
every requested page succeeded. [API reference](https://himalayas.app/docs/remote-jobs-api)

Display a visible Himalayas source link and preserve the supplied
`applicationLink` for every Apply action. Cache responsibly, remove expired
listings, and keep any future keys server-side. Do not redistribute their jobs
to third-party boards, feeds, aggregators, or JobPosting structured data.
[API terms, clause 113](https://himalayas.app/terms)

The per-job API returns 200 for open, 410 for closed, and 404 for absent listings.
Jobs can close early. Check a job before display when using a partial feed;
only reconcile missing records after a successful complete traversal. A timeout,
rate limit, invalid record, or partial run must never close all stored jobs.
[Job status endpoint](https://himalayas.app/docs/remote-jobs-api#how-do-i-check-a-job-is-still-open)

**Greenhouse — secondary.** Use
`GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`.
This is a company-specific board, not a global jobs search; GET needs no key.
Preserve post `id` (not `internal_job_id`), `absolute_url`, `title`,
`updated_at`, `location.name`, and optional `content`. Record the configured
board/company. Before enabling each board, verify its applicable reuse terms,
credit requirements, and refresh limits; public access alone is not a reuse
license. Use conservative daily refresh as our initial policy, honor server
limits, and retire missing posts only after a successful full board response.
[Job Board API](https://docs.greenhouse.io/job-board)

**Adzuna — optional.** Verify India availability, credentials, quotas, attribution,
storage/expiry obligations, and intended-use permission before implementing it.
No LinkedIn/Indeed scraping or replacement scraping when an API fails.

## Milestone 1 acceptance contract

1. Fetch actual published listings with finite timeouts; validate the JSON
   envelope and each record's types before use. Preserve unknown raw fields
   without treating external descriptions or comments as instructions.
2. Use bounded retries for transient connection/timeouts, 429, and selected 5xx
   responses: at most three attempts total, backoff with jitter, honor
   `Retry-After`, and defer a run if the delay is too long. Do not retry ordinary
   4xx or invalid data indefinitely. Authentication errors need configuration
   repair, not repeated requests. An exhausted run fails visibly.
3. Follow returned cursors unchanged, stop at their absence, and detect repeats.
   Record whether the run completed; keep partial results out of missing-job
   reconciliation. Begin with a small, explicitly partial run.
4. Reject/quarantine records missing identity, title, company, or a safe HTTP(S)
   application URL. Keep a reason and source reference for each rejection.
   Never manufacture an ID, application link, salary, or eligibility claim.
5. Deduplicate on `(source, source_id)`. On repeats, upsert changed content and
   preserve first-seen time. For Greenhouse, namespace IDs by board token.
   Similar company/title pairs across sources are possible duplicates only;
   retain provenance and do not auto-merge them in this MVP.
6. Exclude known-expired/closed jobs, record fetch times in UTC, and show freshness
   honestly. If status cannot be verified, withhold the job from the active list
   and retain its stored state for a later successful check.
7. Verify a second ingestion is idempotent: identical source identities do not
   increase the unique count. Report fetched, accepted, rejected, duplicate,
   expired, and stored counts. Never log credentials.

## Normalized record design (implemented in Milestone 1)

One standard-library dataclass represents a job. Normalization is separate from
HTTP so offline unit tests can exercise it. Fields:

| Python fields | Contract / future PostgreSQL representation |
| --- | --- |
| `source`, `source_id` | Required strings; composite UNIQUE constraint. Himalayas uses `guid` verbatim. |
| `title`, `company`, `application_url` | Required strings; TEXT. Keep application URL query parameters. |
| `excerpt`, `description_html`, `employment_type` | Optional strings; nullable TEXT. Render descriptions as text until HTML is safely handled. |
| `salary_min`, `salary_max` | Optional Decimal; NUMERIC. Unknown stays `None`, never zero. |
| `currency`, `salary_period` | Optional strings; retain original units so unequal currencies/periods are not compared as equivalent. |
| `seniority`, `categories` | Optional string lists; JSONB or TEXT[]. |
| `location_restrictions`, `timezone_restrictions` | Location objects with name/optional country code and numeric UTC offsets; optional lists suitable for JSONB. Original shapes remain in raw payload. |
| `source_updated_at`, `expires_at` | Optional UTC-aware datetime; TIMESTAMPTZ. Do not relabel update time as original publication time. |
| `first_seen_at`, `last_seen_at`, `fetched_at` | UTC-aware datetime supplied by ingestion; TIMESTAMPTZ. |
| `is_active`, `raw_payload` | Boolean and original JSON object; BOOLEAN / JSONB. |
| `status`, `status_checked_at`, `validation_issues` | Open/closed/expired/unverified/missing state, UTC check time, and validation diagnostics. |

Missing/null restrictions mean unknown. A source's explicit empty restriction
array can mean unrestricted; do not turn a missing field into that claim.
Invalid optional values become unknown plus a validation issue; missing required
values reject the record. Preserve raw data for diagnosis. Explicitly validate
numeric ranges, timestamps, list items, and URLs rather than coercing everything
to strings. SQL writes will be parameterized and transactional in a later task.

## Day 1 evidence

At 02:39 IST on 17 November 2026, a real unauthenticated request for three jobs
returned HTTP 200 and JSON containing three records. Its raw body, headers, and
capture metadata are in the ignored `data/` folder. These are time-bound
inspection evidence, not a guarantee that those positions remain open.

The response actually contained country-name strings and numeric timezone
offsets, including 5.5. The online data dictionary describes location objects
and timezone strings. Design later validation from observed evidence and handle
documented variants explicitly; do not silently claim India eligibility from an
unrecognized value. The observed `seniority` is a list and some salaries are null.
[Data dictionary](https://himalayas.app/docs/data-dictionary)

## Milestone 1 completion evidence

The implemented CLI fetched three real jobs and verified all three open through
the official per-job API around 02:55 IST on 17 November. There were zero rejected
records and zero status errors. An immediate repeat reused the cache, retained
exactly three records, preserved first-seen timestamps, and kept source IDs and
application URLs unchanged. The run is explicitly a partial feed, not a complete
mirror of Himalayas.

All 74 offline tests pass. Tests cover HTTP/schema errors, timeouts, retries,
rate-limit delays, cursor loops, normalization, duplicates, expiry, status refresh,
safe reconciliation, failed refreshes, and CLI error reporting. PostgreSQL and
later milestones remain unimplemented. See
[MILESTONE_1_REPORT.md](MILESTONE_1_REPORT.md) for the mandatory handoff.


## Manager directive — 17 November 2026 (supersedes earlier phase scope)

Preserve M1 ingestion. Phase 1 adds FastAPI plus deterministic recommendations;
Phase 2 adds PostgreSQL and documented embeddings/semantic retrieval; Phase 3
adds a validated LLM query tool while keeping the core independent of credentials;
Phase 4 evaluates, documents and packages the demo. Defer extra job sources and
elaborate frontends. Report each phase, then advance autonomously. Make local
commits after verified checkpoints, never push without authorization.

Phase 1 acceptance passed: 97 offline tests and a live localhost API response
from a real Spain-eligible listing. Detailed evidence: reports/PHASE_1.md.
