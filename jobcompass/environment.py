"""Load only this repository's local configuration, never shell code."""

import os
from pathlib import Path

from dotenv import dotenv_values

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_environment(names=None):
    """Export missing values; existing process settings win, including blanks.

    No parent-directory search, shell execution or variable interpolation. The
    frontend can select its HTTP setting without importing backend credentials.
    """
    if os.environ.get("PYTHON_DOTENV_DISABLED", "").lower() in {"1", "true", "yes"}:
        return
    for name, value in dotenv_values(ENV_FILE, interpolate=False).items():
        if value is not None and (names is None or name in names):
            os.environ.setdefault(name, value)
