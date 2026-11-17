"""Measured ranking metrics on an explicitly labeled, fingerprinted corpus."""

import argparse
import json
import math
from datetime import datetime
from pathlib import Path

from .search import SearchParams, filter_jobs, rank_jobs
from .semantic import content_hash, recommend_semantic
from .environment import load_environment

load_environment()


def precision_at_k(grades, k):
    if k < 1:
        raise ValueError("k must be positive")
    return sum(grade > 0 for grade in grades[:k]) / k


def ndcg_at_k(grades, all_grades, k):
    if k < 1:
        raise ValueError("k must be positive")
    def dcg(values):
        return sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(values[:k]))
    ideal = dcg(sorted(all_grades, reverse=True))
    return dcg(grades) / ideal if ideal else None


def evaluate(snapshot, labels, mode="deterministic", k=3):
    if k < 1 or mode not in {"deterministic", "hybrid"}:
        raise ValueError("Invalid evaluation mode or k")
    records = snapshot["records"]
    actual = {row["source_id"]: content_hash(row) for row in records if row["source"] == labels["source"]}
    if len(actual) != len(records) or actual != labels["corpus"]:
        raise ValueError("Evaluation corpus changed; review and relabel before measuring")
    # Evaluate relevance as of this captured snapshot, not a fabricated current status.
    as_of = datetime.fromisoformat(snapshot["run_at"])
    cases = []
    for case in labels["cases"]:
        relevance = case["relevance"]
        if set(relevance) != set(actual) or any(type(grade) is not int or not 0 <= grade <= 3 for grade in relevance.values()):
            raise ValueError("Every corpus record must have an explicit relevance grade 0–3")
        params = SearchParams(**case["params"])
        if mode == "hybrid":
            ranked = recommend_semantic(records, params, as_of)
        else:
            ranked = rank_jobs(filter_jobs(records, params, as_of, keyword_mode="any"), params.q)
        grades = [relevance[row["source_id"]] for row in ranked]
        positive = any(relevance.values())
        cases.append({"id": case["id"], "params": case["params"], "ranked_ids": [row["source_id"] for row in ranked[:k]],
            "precision_at_k": precision_at_k(grades, k), "ndcg_at_k": ndcg_at_k(grades, list(relevance.values()), k),
            "has_relevant_jobs": positive, "empty_result_correct": not ranked if not positive else None})
    positive_cases = [case for case in cases if case["has_relevant_jobs"]]
    return {"mode": mode, "k": k, "corpus_size": len(records), "query_count": len(cases),
        "label_source": labels["label_source"], "snapshot_as_of": snapshot["run_at"],
        "macro_precision_at_k": sum(c["precision_at_k"] for c in positive_cases) / len(positive_cases) if positive_cases else None,
        "macro_ndcg_at_k": sum(c["ndcg_at_k"] for c in positive_cases) / len(positive_cases) if positive_cases else None,
        "aggregation": "Macro means include only queries with relevant labeled jobs; negative queries report empty-result correctness separately. Precision divides by k, even when fewer jobs are returned.",
        "cases": cases}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--labels", type=Path, default=Path("evaluations/real_jobs.json"))
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()
    snapshot = json.loads((args.data_dir / "jobs.json").read_text())
    labels = json.loads(args.labels.read_text())
    result = [evaluate(snapshot, labels, mode, args.k) for mode in ("deterministic", "hybrid")]
    output = args.data_dir / f"evaluation-k{args.k}.json"
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps([{key: value for key, value in report.items() if key != "cases"} for report in result], indent=2))
    print(f"Saved: {output.resolve()}")


if __name__ == "__main__":
    main()
