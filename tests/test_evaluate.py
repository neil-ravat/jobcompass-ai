import math

import pytest

from jobcompass.evaluate import evaluate, ndcg_at_k, precision_at_k
from jobcompass.normalize import normalize_job
from jobcompass.semantic import content_hash


def test_metrics_use_real_rank_positions_and_fixed_k():
    assert precision_at_k([3], 3) == pytest.approx(1/3)
    assert precision_at_k([], 3) == 0
    assert ndcg_at_k([3, 2, 0], [0, 2, 3], 3) == 1
    assert ndcg_at_k([0, 3], [3, 0], 2) == pytest.approx(1/math.log2(3))
    assert ndcg_at_k([], [0, 0], 3) is None
    with pytest.raises(ValueError):
        precision_at_k([1], 0)


def test_evaluation_requires_current_corpus_and_complete_labels(raw_job, now):
    row = {**normalize_job(raw_job, now).to_record(), "status": "open", "is_active": True, "status_checked_at": now.isoformat()}
    snapshot = {"records": [row], "run_at": now.isoformat()}
    labels = {"source": "himalayas", "label_source": "unit test only", "corpus": {row["source_id"]: content_hash(row)},
              "cases": [{"id": "python", "params": {"q": "python"}, "relevance": {row["source_id"]: 3}}]}
    result = evaluate(snapshot, labels, k=1)
    assert result["macro_precision_at_k"] == result["macro_ndcg_at_k"] == 1
    labels["cases"][0]["relevance"] = {}
    with pytest.raises(ValueError, match="explicit relevance"):
        evaluate(snapshot, labels)
    labels["corpus"][row["source_id"]] = "outdated"
    with pytest.raises(ValueError, match="corpus changed"):
        evaluate(snapshot, labels)
