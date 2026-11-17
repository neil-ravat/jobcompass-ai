"""Explicit database/index operations: python -m jobcompass.manage COMMAND."""

import argparse
import json
import os
import sys
from pathlib import Path

from .environment import load_environment

load_environment()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "sync", "embed"])
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("JOBCOMPASS_DATA_DIR", "data")))
    args = parser.parse_args()
    try:
        if args.command == "migrate":
            from .database import migrate
            result = {"applied": migrate()}
        else:
            snapshot = json.loads((args.data_dir / "jobs.json").read_text())
            if args.command == "sync":
                from .database import upsert_snapshot
                result = {"stored": upsert_snapshot(snapshot)}
            else:
                from .semantic import build_index
                result = build_index(snapshot, args.data_dir)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as error:
        # Do not echo a connection string or provider credential in CLI errors.
        print(f"{args.command} failed ({type(error).__name__}). Check configuration, migrations, and local logs.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
