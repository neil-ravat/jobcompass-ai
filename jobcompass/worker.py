"""Single-process refresh loop sharing the existing source and status caches."""

import argparse
import json
import os
import time
from pathlib import Path

import requests

from .himalayas import RetryDeferred, _retry_delay
from .ingest import ingest
from .environment import load_environment

load_environment()


def refresh_once(data_dir, limit=20, max_pages=1, semantic=False):
    snapshot = ingest(data_dir, limit=limit, max_pages=max_pages)
    if os.environ.get("DATABASE_URL"):
        from .database import upsert_snapshot
        upsert_snapshot(snapshot)
    index_result = {"enabled": semantic}
    if semantic:
        from .semantic import MODEL, DIMENSIONS, build_index, content_hash, validate_vector
        path = Path(data_dir) / "embeddings.json"
        try:
            previous = json.loads(path.read_text())
            existing = {(row["source"], row["source_id"]): row["content_hash"] for row in previous["rows"]}
            expected = {(row["source"], row["source_id"]): content_hash(row) for row in snapshot["records"]}
            for entry in previous["rows"]:
                validate_vector(entry["vector"])
            reusable = previous["model"] == MODEL and previous["dimensions"] == DIMENSIONS and existing == expected and len(previous["rows"]) == len(expected)
        except (OSError, ValueError, TypeError, KeyError):
            reusable = False
        if reusable:
            if os.environ.get("DATABASE_URL"):
                from .database import save_vectors
                save_vectors(previous["rows"], MODEL)
            index_result = {"reused": True, "indexed": len(previous["rows"])}
        else:
            index_result = {"reused": False, **build_index(snapshot, data_dir)}
    return {"counts": snapshot["counts"], "feed_cache_used": snapshot["feed_cache_used"],
            "index": index_result, "degraded": bool(snapshot["status_errors"] or snapshot["rejected_records"])}


def retry_wait(error, interval):
    if isinstance(error, RetryDeferred):
        return max(interval, error.retry_after or interval)
    if isinstance(error, requests.HTTPError) and error.response is not None:
        try:
            return max(interval, _retry_delay(error.response, 0))
        except RetryDeferred as deferred:
            return max(interval, deferred.retry_after or interval)
    return interval


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("JOBCOMPASS_DATA_DIR", "data")))
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--interval", type=int, default=300)
    parser.add_argument("--semantic", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.interval < 60 or not 1 <= args.limit <= 20 or args.max_pages < 1:
        parser.error("interval must be >=60, limit 1–20, max-pages >=1")
    try:
        while True:
            delay = args.interval
            try:
                result = refresh_once(args.data_dir, args.limit, args.max_pages, args.semantic)
                print(json.dumps(result), flush=True)
                code = 2 if result["degraded"] else 0
            except Exception as error:
                delay = retry_wait(error, args.interval)
                print(json.dumps({"error": type(error).__name__, "retry_in_seconds": delay}), flush=True)
                code = 1
            if args.once:
                return code
            time.sleep(delay)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
