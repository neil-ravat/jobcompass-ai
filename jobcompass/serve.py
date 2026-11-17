"""Start the local FastAPI server with environment-backed bind settings."""

import os

import uvicorn

from .environment import load_environment


def main():
    load_environment()
    try:
        port = int(os.environ.get("JOBCOMPASS_PORT", "8765"))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise SystemExit("JOBCOMPASS_PORT must be an integer from 1 to 65535") from None
    uvicorn.run("jobcompass.api:app", host=os.environ.get("JOBCOMPASS_HOST", "127.0.0.1"), port=port)


if __name__ == "__main__":
    main()
