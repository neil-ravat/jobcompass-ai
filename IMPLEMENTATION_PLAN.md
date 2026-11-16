# JobCompass implementation plan and status

Updated 17 November 2026. Target: working, tested, interview-ready MVP by
23 November 2026. The latest manager directive supersedes the initial teaching-only
workflow and earlier deferred PostgreSQL/AI scope. Codex may implement and advance
sequentially after reporting each checkpoint. Do not push without authorization.

## Completed and attempted phases

| Milestone | Acceptance evidence | Status |
| --- | --- | --- |
| M1 real ingestion | 74 tests; three actual Himalayas jobs; repeat preserved identities and first-seen time | Complete |
| P1 FastAPI and deterministic recommendations | 97 tests; real filtered localhost response; commit 10b88d5 | Complete |
| P2 PostgreSQL and semantic retrieval | 110 tests including real DB queries; three stored jobs/vectors; real hybrid result; commit 4efcacf | Complete |
| P3 optional LLM query tool | 126 tests; validated tool flow and failures; live missing-key 503; commit f77c7ac | Implemented; successful live LLM call unverified |
| P4 evaluation and delivery | 136 tests; labeled evaluation, refresh/demo scripts, live endpoint checks, Docker configuration validation | Local delivery verified; container build/deployment unverified |

## Non-negotiable data rules

Use actual permitted API responses only. Synthetic job records belong in tests.
Preserve source identity, original Apply URLs, attribution and timestamps. Keep
missing eligibility distinct from unrestricted eligibility. Respect refresh and
rate limits, hide expired/closed/unverified jobs, and never retire missing records
from a partial or failed feed. Never substitute fabricated data after an error.

Himalayas is the primary source. Greenhouse/Adzuna remain deferred until the
primary MVP is validated more broadly. No LinkedIn/Indeed scraping, elaborate
frontend, distributed worker infrastructure or multi-agent framework is planned.

## Current architecture

Existing normalization and ingestion produce an atomic JSON snapshot. With
DATABASE_URL set, idempotent PostgreSQL upserts preserve provenance and status.
MiniLM embeddings are stored locally and in pgvector. FastAPI hard filters precede
lexical or semantic scoring. The optional LLM produces a validated search tool
call; explicit user constraints and final ranking stay in Python. A single refresh
worker shares the daily feed and ten-minute status caches.

## Remaining verification and exact next work

1. Configure a valid LLM key only if a live agent demonstration is required;
   execute one bounded query and verify its interpretation against hard constraints.
2. At the next permitted daily feed refresh, ingest a broader real corpus, then
   obtain independent relevance judgments and repeat evaluation. Current labels
   are Codex-assigned on three listings and cannot establish general quality.
3. Optionally build and run the provided container configuration. It has only
   passed configuration parsing; no remote deployment or push is authorized.
4. Walk through the code and tests for interview understanding. No user-written
   Python was submitted in these milestones; implementation was Codex-generated.

No new feature milestone is automatically starting after this delivery.

## Handoff policy and references

Every major milestone, completed or attempted, requires a report with requirements,
implemented behavior, changed files, functions/endpoints/database changes, actual
commands/results, limitations, decisions, authorship, interview concepts and exact
next work. End with Evidence Needed for Verification. Never infer completion from
file existence. Reports: MILESTONE_1_REPORT.md and reports/PHASE_1.md through
reports/PHASE_4.md. README.md reproduces the local demo; docs/INTERVIEW.md explains
its implementation. Repository-wide working instructions are in AGENTS.md.
