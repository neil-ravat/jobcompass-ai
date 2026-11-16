import json

import pytest

from jobcompass import semantic
from jobcompass.normalize import normalize_job
from jobcompass.search import SearchParams


@pytest.fixture
def row(raw_job, now):
    return {**normalize_job(raw_job, now).to_record(), "is_active": True, "status": "open", "status_checked_at": now.isoformat()}


def test_hard_constraints_run_before_semantic_search(monkeypatch, row, now):
    other = {**row, "source_id": "other", "location_restrictions": [{"name": "United States", "country_code": "US"}]}
    calls = []
    def scores(records, query):
        calls.extend(records)
        return {(r["source"], r["source_id"]): 0.5 for r in records}
    monkeypatch.setattr(semantic, "semantic_scores", scores)
    result = semantic.recommend_semantic([other, row], SearchParams(q="software", country="IN"), now)
    assert len(result) == len(calls) == 1
    assert result[0]["source_id"] == row["source_id"]
    assert result[0]["score_components"]["semantic"] == 35


def test_json_vector_index_and_stale_content(monkeypatch, tmp_path, row):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("JOBCOMPASS_DATA_DIR", str(tmp_path))
    vector = [1.0] + [0.0] * 383
    monkeypatch.setattr(semantic, "embed_texts", lambda texts: [vector for text in texts])
    assert semantic.build_index({"records": [row]}, tmp_path)["indexed"] == 1
    scores = semantic.semantic_scores([row], "anything")
    assert scores[(row["source"], row["source_id"])] == 1
    with pytest.raises(semantic.SemanticUnavailable, match="outdated"):
        semantic.semantic_scores([{**row, "title": "changed"}], "anything")


@pytest.mark.parametrize("vector", [[], [0]*384, [float("nan")]*384, [1]*383])
def test_invalid_vectors(vector):
    with pytest.raises(ValueError):
        semantic.validate_vector(vector)


def test_hybrid_tie_break_is_stable(row):
    other = {**row, "source_id": "aaa"}
    similarities = {(r["source"], r["source_id"]): 0.5 for r in [row, other]}
    assert semantic.hybrid_rank([row, other], "python", similarities) == semantic.hybrid_rank([other, row], "python", similarities)


def test_empty_eligible_pool_needs_no_model(monkeypatch, row, now):
    monkeypatch.setattr(semantic, "embed_texts", lambda texts: pytest.fail("Model must not run"))
    assert semantic.recommend_semantic([row], SearchParams(q="software", country="US"), now) == []
