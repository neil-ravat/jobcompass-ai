# JOB COMPASS — URGENT PROJECT MANAGER DIRECTIVE

**Date:** 17 November 2026
**Target:** Working, tested, interview-ready MVP by 23 November 2026
**Priority:** CRITICAL — Primary project

## Current milestone assessment

M1 — Real Job Data Ingestion has been reported as implemented.

Evidence reported:
- 74 offline tests passed.
- Three real Himalayas jobs were fetched, validated and stored.
- Pagination, caching, deduplication, expiry management, HTTP retries and error handling implemented.
- No PostgreSQL, FastAPI endpoints, embeddings, recommendation engine, LLM integration or deployment yet.
- No commits currently exist.
- These claims come from your handoff report and have not been independently audited.

**Manager decision:** Preserve the existing ingestion implementation. Advance toward a complete working job-recommendation system. Do not waste time rebuilding features that already work.

## Immediate execution order

### Phase 1 — API and deterministic recommendation MVP (P0)

1. Rerun the existing tests to establish a clean baseline.
2. Implement a minimal FastAPI application using the existing ingestion models.
3. Expose `/health`, `/jobs` and `/recommendations`.
4. Implement keyword/role matching, remote-work filtering, country eligibility and salary constraints where available.
5. Distinguish unrestricted, restricted and unknown eligibility. Never interpret missing source data as confirmed eligibility.
6. Implement deterministic ranking with explainable score components.
7. Add pagination, input validation and clear error responses.
8. Add automated tests covering filtering, ranking, tie-breaking, invalid inputs and empty results.

**Acceptance:** The API returns real normalized jobs, applies hard constraints correctly and provides deterministic, understandable recommendations.

### Phase 2 — PostgreSQL and semantic retrieval (P0)

1. Create a PostgreSQL schema with source identity, normalized job fields, provenance and timestamps.
2. Add migrations and idempotent upserts.
3. Preserve job status and expiry information.
4. Add embeddings for semantic job search using a documented model.
5. Implement vector similarity search using PostgreSQL/pgvector where practical.
6. Combine semantic relevance with hard constraints and deterministic ranking.
7. Test persistence, duplicate handling, retrieval and invalid or missing data.

**Acceptance:** A job can move from the source API into persistent storage and appear in a semantic search result with the original application URL.

If local database setup becomes a blocker, retain a functioning JSON-backed demo, report PostgreSQL as incomplete and continue building the MVP. Never claim PostgreSQL works without a tested connection and queries.

### Phase 3 — Minimal AI career-agent layer (P1)

1. Add one LLM-assisted job-query workflow.
2. Use explicit, validated tool schemas.
3. Let the LLM interpret user intent and call the existing search/recommendation functions.
4. Keep eligibility checks and final ranking constraints in deterministic Python code.
5. Return structured, source-grounded results.
6. Handle unavailable LLM credentials, malformed tool calls and empty retrieval safely.
7. Ensure the core recommendation API continues working without an LLM.

Avoid unnecessary multi-agent frameworks.

### Phase 4 — Evaluation and delivery (P0)

1. Add representative labeled query/job cases.
2. Evaluate ranking correctness and retrieval relevance with appropriate metrics such as Precision@K and NDCG@K, wherever ground-truth labels exist.
3. Test API failures, data freshness and source attribution.
4. Produce a reproducible local demonstration and setup guide.
5. Add deployment configuration if feasible.
6. Record actual test outcomes, limitations and measured results.
7. Create clean local Git commits after successful checkpoints, excluding secrets and runtime data. Do not push without authorization.

## Scope restrictions

Do not prioritize Greenhouse, Adzuna, elaborate frontends, distributed infrastructure or complex agent orchestration until the primary MVP works.

Do not break existing functionality. Do not fabricate data, recommendation quality, benchmarks or deployments.

## Execution policy

**Begin coding immediately. This is an implementation directive, not a request for another plan.**

Proceed through phases sequentially, with tests and a concise milestone report after each phase. You may advance autonomously when the phase passes its acceptance criteria. If blocked, record the exact blocker and continue with the highest-value independent task.

Keep changes focused, maintainable and interview-explainable. Do not request conceptual explanations or quizzes from the user.

## Required progress report

After each milestone, provide:

- Milestone and implementation status.
- Exact files created or changed.
- Features demonstrably working.
- Commands executed and actual test results.
- Real API/database response examples, sanitized where necessary.
- Bugs fixed and remaining blockers.
- What is incomplete or unverified.
- Architecture decisions and tradeoffs.
- Next highest-priority coding task.
- Codex-generated work versus user-written work.
- Git commit hash, only when a commit exists.

**Final deliverable:** A functioning JobCompass system demonstrating real job ingestion, filtering, explainable recommendation, semantic retrieval, basic AI integration where feasible, testing, and an interview-ready README/demo.

Optimize for working software by 23 November 2026, not architectural complexity.
