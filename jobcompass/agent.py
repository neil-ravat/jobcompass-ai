"""One bounded LLM tool call interprets intent; Python owns search and constraints."""

import json
import os
from typing import Literal

import requests
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .search import SearchParams


class AgentUnavailable(RuntimeError):
    pass


class InvalidToolCall(RuntimeError):
    pass


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=4000, pattern=r"\S")
    constraints: SearchParams | None = None
    mode: Literal["deterministic", "hybrid"] = "deterministic"


class SearchToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    q: str = Field(min_length=1, max_length=300)
    role: str | None = Field(max_length=120)
    country: str | None = Field(max_length=100)
    remote_only: bool
    min_salary: float | None = Field(ge=0, le=10**12, allow_inf_nan=False)
    currency: str | None = Field(min_length=3, max_length=3)
    salary_period: Literal["hourly", "weekly", "fortnightly", "monthly", "annual"] | None
    limit: int = Field(ge=1, le=20)


def tool_definition():
    return {"type": "function", "name": "search_jobs", "description": "Search verified real job records using explicit user constraints.",
            "strict": True, "parameters": SearchToolArguments.model_json_schema()}


def interpret_query(request: AgentRequest) -> SearchParams:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise AgentUnavailable("OPENAI_API_KEY is not configured. /recommendations and /search work without an LLM.")
    locked = request.constraints.model_dump(mode="json", exclude_unset=True, exclude_none=True) if request.constraints else {}
    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=(5, 30),
            json={
                "model": os.environ.get("OPENAI_MODEL", "gpt-5.4-mini"),
                "store": False, "max_output_tokens": 1200,
                "instructions": (
                    "Interpret the user's job-search intent by calling search_jobs once. "
                    "Use concise skill/role keywords as q. Extract only stated constraints; "
                    "use null for unspecified role, country, salary, currency or pay period. "
                    "Default remote_only to true and limit to 10. Do not infer location, salary "
                    "or eligibility. Only set a salary floor when its currency and period are explicit. "
                    "Respect all supplied locked constraints. Do not invent job records or application URLs."
                ),
                "input": [{"role": "user", "content": json.dumps({"message": request.message, "locked_constraints": locked})}],
                "tools": [tool_definition()],
                "tool_choice": {"type": "function", "name": "search_jobs"},
                "parallel_tool_calls": False,
            },
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise AgentUnavailable("LLM request failed or timed out. The core recommendation endpoints remain available.") from error
    try:
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("status") != "completed":
            raise ValueError("Incomplete provider response")
        output = payload["output"]
        if not isinstance(output, list) or not all(isinstance(item, dict) for item in output):
            raise ValueError("Invalid output array")
        calls = [item for item in output if item.get("type") == "function_call"]
        if len(calls) != 1 or calls[0].get("name") != "search_jobs":
            raise ValueError("Expected exactly one search_jobs call")
        arguments = SearchToolArguments.model_validate_json(calls[0]["arguments"])
        # Validate extracted intent first, then enforce user-supplied constraints again.
        parsed = SearchParams.model_validate(arguments.model_dump())
        return SearchParams.model_validate({**parsed.model_dump(), **locked})
    except (ValueError, TypeError, KeyError, ValidationError) as error:
        raise InvalidToolCall("LLM returned an invalid search request; no search was executed.") from error
