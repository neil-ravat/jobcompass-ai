"""Run with python -m jobcompass; no web server or database is required."""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

from .ingest import ingest


def main():
    parser = argparse.ArgumentParser(description="Ingest real remote jobs from Himalayas.")
    parser.add_argument("--limit", type=int, default=20, help="Jobs per page, 1–20 (default: 20)")
    parser.add_argument("--max-pages", type=int, default=1, help="Page cap (default: 1; usually a partial feed)")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    args = parser.parse_args()
    try:
        result = ingest(args.data_dir, args.limit, args.max_pages)
        if os.environ.get("DATABASE_URL"):
            try:
                from .database import upsert_snapshot
                upsert_snapshot(result)
            except Exception:
                print("JSON ingestion succeeded, but PostgreSQL sync failed. Check migrations and connection.", file=sys.stderr)
                return 1
    except (requests.RequestException, ValueError, TypeError, KeyError, OSError) as error:
        print(f"Ingestion failed: {error}", file=sys.stderr)
        return 1
    print("Jobs sourced from Himalayas — https://himalayas.app")
    print(json.dumps({key: value for key, value in result.items() if key != "records"}, indent=2))
    print(f"Saved: {(args.data_dir / 'jobs.json').resolve()}")
    print("Apply using each record's original application_url.")
    return 2 if result["status_errors"] or result["rejected_records"] else 0


if __name__ == "__main__":
    sys.exit(main())
