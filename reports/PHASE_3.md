# Milestone Handoff Report — JobCompass P3

## Project, status and requirements

17 November 2026. P3 — Minimal LLM career-query layer — implemented and tested
with mocked provider responses; successful live LLM inference is unverified.
Required: validated tools, intent interpretation, deterministic eligibility/ranking,
source-grounded results, safe missing credentials/malformed calls/empty retrieval,
and independent operation of the core API.

## Implemented behavior

POST /agent/query accepts a message, optional explicit constraints and a search
mode. One bounded OpenAI Responses API request is forced to call search_jobs.
Strict JSON Schema and Pydantic validate every argument. Explicit user constraints
are reapplied in Python. The existing deterministic or hybrid search functions
produce the result records and source links; the LLM does not generate job facts.
No source job descriptions are transmitted to the provider. Missing credentials
return 503, malformed tool output 502, invalid client input 422, and genuine empty
retrieval returns an empty list. Core /jobs, /recommendations and /search remain
independent of OPENAI_API_KEY.

## Files created or modified

Created jobcompass/agent.py, tests/test_agent.py, reports/PHASE_3.md.
Modified jobcompass/api.py and reports/PHASE_2.md. No database/schema change.

## Functions, classes and endpoints

AgentRequest, SearchToolArguments, tool_definition(), interpret_query();
POST /agent/query; outbound POST https://api.openai.com/v1/responses.
OPENAI_MODEL is configurable, default gpt-5.4-mini. Credentials come only from
OPENAI_API_KEY. One request, finite connection/read timeouts, limited output,
store=false, and no parallel tool calls. No multi-agent framework was introduced.

## Actual verification

`TEST_DATABASE_URL=postgresql://jobcompass@127.0.0.1:55432/jobcompass_test .venv/bin/python -m pytest -q --tb=short`:
**126 passed**, including PostgreSQL checks. One upstream test-client deprecation
warning. Added tests cover strict schema, locked constraints, absent key, timeout,
HTTP/connection errors, extra fields, missing fields, wrong/duplicate tool calls,
invalid JSON/country, incomplete response, empty retrieval and invalid body.
Live localhost POST /agent/query returned **HTTP 503**, code llm_unavailable,
with instructions to configure a key or use the core endpoints. Response saved
at data/evidence/phase3-api.json. No paid request was made and no live model
interpretation quality is claimed.

## Bugs, blockers and incomplete verification

No failing tests observed. Exact blocker: OPENAI_API_KEY is absent from the runtime.
A successful provider request, account/model access, latency, cost and natural
language extraction quality are not verified. Prompt interpretation can still
be wrong despite schema validity; the response exposes interpreted parameters.
The core source constraints cannot be relaxed by a model tool response when the
user provided explicit constraint fields. Only one tool and one model call are
supported; conversation memory and autonomous application submission are out of scope.

## Architecture decisions

Use the LLM as an intent parser, then execute the existing Python search functions.
Return structured retrieval results directly, avoiding a second generative pass.
This limits complexity and provides inspectable provenance. Without a key, fail
clearly instead of presenting a deterministic parser as an LLM interaction.

## Authorship and interview concepts

Codex generated implementation/tests/docs; the user supplied requirements. No
user-written code was submitted. Understand function calling versus execution,
strict schemas, runtime validation, untrusted model output, constrained tool
permissions, grounded retrieval, explicit-user-constraint precedence, and graceful
capability failure.

## Next milestone

P4 — Evaluation and delivery. Add explicitly labeled cases and ranking metrics,
refresh/demo tooling, setup/deployment configuration and final regression evidence.
Continue under the manager directive while documenting the blocked live LLM check.

## Evidence Needed for Verification

Inspect tests/test_agent.py and data/evidence/phase3-api.json. To verify the full
provider path, configure a valid OPENAI_API_KEY locally, select an account-supported
OPENAI_MODEL, then run a bounded query and compare interpreted constraints with
retrieved source records. No successful live LLM evidence currently exists.
Official documentation used:
https://developers.openai.com/api/docs/guides/function-calling
https://developers.openai.com/api/docs/models/gpt-5.4-mini
