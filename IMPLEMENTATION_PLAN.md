# JobCompass implementation plan and status

Updated 17 November 2026. Target: working, tested, interview-ready MVP by
23 November 2026. The latest manager directive supersedes the initial teaching-only
workflow and earlier deferred PostgreSQL/AI scope. After S1 acceptance, the user
explicitly authorized one frontend milestone (F1). The integrated local MVP is
ready for independent review with the limitations below. Stop after F1 delivery;
do not push, deploy or start another feature milestone without authorization.
The subsequent explicit SEC1 security directive authorizes private environment
configuration and publication-safety verification only; it does not authorize a push.
The later explicit PUB1 directive authorized public source publication to
https://github.com/neil-ravat/jobcompass-ai on `main`. The audited application
history is now published; no application deployment or new feature work is implied.

## Completed and attempted phases

| Milestone | Acceptance evidence | Status |
| --- | --- | --- |
| M1 real ingestion | 74 tests; three actual Himalayas jobs; repeat preserved identities and first-seen time | Complete |
| P1 FastAPI and deterministic recommendations | 97 tests; real filtered localhost response; commit 10b88d5 | Complete |
| P2 PostgreSQL and semantic retrieval | 110 tests including real DB queries; three stored jobs/vectors; real hybrid result; commit 4efcacf | Complete |
| P3 optional LLM query tool | 126 tests; validated tool flow and failures; live missing-key 503; commit f77c7ac | Implemented; successful live LLM call unverified |
| P4 evaluation and delivery | 136 tests; labeled evaluation, refresh/demo scripts, live endpoint checks, Docker configuration validation | Local delivery verified; container build/deployment unverified |
| S1 final stabilization | 136 tests in existing and clean environments; fresh PostgreSQL/pgvector/model initialization; Docker build and local endpoint checks; repeated evaluation and Git exclusions | Ready for independent local review; larger corpus awaits permitted refresh |
| F1 professional frontend | 156 tests; real HTTP browser searches/filters; desktop and narrow screenshots; backend image rebuild | Integrated Streamlit application verified locally |
| F1 final UI polish | 162 tests; 12 real browser checks at 1440px, 390px and 320px; labeled filter access, actual timestamps and source-preserving typography | Bounded corrections verified; backend unchanged |
| SEC1 environment security | 172 tests; private mode-600 .env; SCRAM PostgreSQL; native/Compose checks; Git history and build-context audit | Local configuration verified; no publication performed |
| PUB1 authorized GitHub publication | Account/name verified; redacted history scan; preserved commit history; all 76 application-snapshot file hashes matched remote main | Public source published; no application deployment |

## Non-negotiable data rules

Use actual permitted API responses only. Synthetic job records belong in tests.
Preserve source identity, original Apply URLs, attribution and timestamps. Keep
missing eligibility distinct from unrestricted eligibility. Respect refresh and
rate limits, hide expired/closed/unverified jobs, and never retire missing records
from a partial or failed feed. Never substitute fabricated data after an error.

Himalayas is the primary source. Greenhouse/Adzuna remain deferred until the
primary MVP is validated more broadly. No LinkedIn/Indeed scraping, distributed
worker infrastructure or multi-agent framework is planned. F1 is the separately
authorized Streamlit frontend, not a new ingestion or ranking architecture.

## Current architecture

Existing normalization and ingestion produce an atomic JSON snapshot. With
DATABASE_URL set, idempotent PostgreSQL upserts preserve provenance and status.
MiniLM embeddings are stored locally and in pgvector. FastAPI hard filters precede
lexical or semantic scoring. The optional LLM produces a validated search tool
call; explicit user constraints and final ranking stay in Python. A single refresh
worker shares the daily feed and ten-minute status caches.
Streamlit calls the HTTP API and presents its results; it never reads PostgreSQL,
local job files or embedding artifacts. API responses add readable plain-text
descriptions while retaining the existing fields and ranking behavior.

## Remaining verification and exact next work

1. Independent review of the public source and local application is next.
   Reproduce the README demo and inspect reports/GITHUB_PUBLICATION.md and SEC1 alongside F1/S1.
2. The verified feed was fetched 16 November at 21:24:54.988908 UTC. Its next
   permitted refresh is 18 November at 02:54:54.988908 IST. The existing worker
   requests 20 jobs on one page then, provided it remains running. Expansion was
   not forced during stabilization; three actual jobs remain in the corpus.
   Review new relevance labels independently and rerun evaluation after growth;
   current Codex-authored labels are unreviewed and fingerprints will reject a
   changed corpus. Current scores do not establish general retrieval quality.
3. A successful live LLM call remains optional and unverified. Missing-key 503
   behavior passed locally and in Docker; delivery does not depend on a key.
   Containers were built and verified locally; remote deployment is unverified
   and no push or deployment is authorized.
4. Walk through the code and tests for interview understanding. No user-written
   Python was submitted in these milestones; implementation was Codex-generated.

No new feature milestone is automatically starting after this delivery.

## Handoff policy and references

Every major milestone, completed or attempted, requires a report with requirements,
implemented behavior, changed files, functions/endpoints/database changes, actual
commands/results, limitations, decisions, authorship, interview concepts and exact
next work. End with Evidence Needed for Verification. Never infer completion from
file existence. Reports: MILESTONE_1_REPORT.md and reports/PHASE_1.md through
reports/PHASE_4.md, reports/FINAL_STABILIZATION.md, reports/FRONTEND_F1.md and
reports/FRONTEND_F1_POLISH.md.
README.md reproduces the local demo; docs/INTERVIEW.md explains
its implementation. Repository-wide working instructions are in AGENTS.md.
