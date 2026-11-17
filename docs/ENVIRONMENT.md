# Local environment configuration and publication safety

The backend entry points load only the repository-root `.env`. Exported process
values win, including an explicitly empty `DATABASE_URL`. Values are parsed as
data: no shell execution, variable expansion or parent-directory search. The
Streamlit HTTP client loads only `JOBCOMPASS_API_URL`; it does not import database
or provider credentials from the file. Restart services after changing settings.

## Configuration inventory

| Variable | Consumer and purpose |
| --- | --- |
| `DATABASE_URL` | Backend PostgreSQL endpoint/database; blank explicitly selects JSON storage. Keep the password out of the URL. |
| `PGPASSWORD` | Native PostgreSQL driver authentication. Compose injects it into API/worker and maps it to the database container's `POSTGRES_PASSWORD`. |
| `TEST_DATABASE_URL` | Dedicated PostgreSQL integration-test database; its name must end in `_test`. |
| `JOBCOMPASS_DATA_DIR` | Backend snapshots, source/status caches and local vector-index files. |
| `JOBCOMPASS_MODEL_CACHE` | Local FastEmbed model cache. |
| `JOBCOMPASS_HOST` | Native FastAPI bind address through `python -m jobcompass.serve`; defaults to loopback. |
| `JOBCOMPASS_PORT` | Native FastAPI port and Compose's loopback-only published API port. |
| `JOBCOMPASS_API_URL` | Streamlit's HTTP backend URL; must not contain credentials. |
| `HIMALAYAS_API_KEY` | Optional source Authorization header; absent for the verified public-source setup. |
| `OPENAI_API_KEY` | Optional LLM Authorization header; never required for core search. |
| `OPENAI_MODEL` | Existing optional LLM model selection. |
| `PYTHON_DOTENV_DISABLED` | Set to `1` to disable local file loading; Compose uses injected values and tests isolate local configuration. |

Compose's `POSTGRES_USER` and `POSTGRES_DB` are fixed non-secret container
initialization identifiers. `POSTGRES_PASSWORD` is derived at runtime from
`PGPASSWORD`, not a second credential stored in source. Container data/model paths
remain `/app/data` and `/app/data/models`; native path settings do not remap volumes.
Streamlit's own loopback address and port remain in `.streamlit/config.toml`.
Standard framework, Python and libpq environment options are not additional
JobCompass-specific settings.

## Local setup

This workspace already has a real `.env` with mode `600` and a generated database
password configured on its isolated local PostgreSQL cluster. Optional provider
keys were not available and were not added. The native cluster now requires SCRAM
password authentication on TCP and local sockets; it listens only on loopback.

On another checkout, create a private file and edit values locally:

```bash
umask 077
cp .env.example .env
chmod 600 .env
```

Do not overwrite an existing `.env`. Enter your database's real password locally
in `PGPASSWORD`; the template deliberately leaves it blank. Use the fresh
PostgreSQL setup in README if the database does not exist. Editing the file does
not change an existing database password. Never paste credentials into chat,
commit them, use shell `source`/`set -x`, or print the environment for debugging.

From the repository root, after PostgreSQL is running:

```bash
uv sync --locked --all-extras
.venv/bin/python -m jobcompass.manage migrate
bash scripts/demo.sh
# In another terminal:
.venv/bin/python -m streamlit run frontend/app.py
```

`demo.sh` starts the existing API/worker with a restrictive file-creation mask and
preserves source refresh limits. To start only the API, use
`.venv/bin/python -m jobcompass.serve`. The raw Uvicorn CLI still loads database/API
settings when importing the app, but its CLI controls the bind address and port.

The core application works without either optional provider key. To explicitly
choose JSON storage despite an existing `.env`, run `DATABASE_URL= bash scripts/demo.sh`.

## Tests and Docker

```bash
.venv/bin/python -m pytest -q
docker compose --env-file .env config --quiet
docker compose build
```

Tests load only `TEST_DATABASE_URL` and `PGPASSWORD` from the local file; they
disable application file loading and clear application/provider settings. Mocked
provider tests use ephemeral generated tokens and make no real provider requests.
Without a dedicated test URL the four PostgreSQL integration tests skip.

Compose reads `.env` for runtime interpolation and injects only each service's
needed variables. Do not print plain `docker compose config`, `docker inspect`,
environment dumps or traced commands: runtime configuration can contain secrets.
Use `config --quiet` for validation. A missing/empty password fails Compose
validation. For a new volume, the database initializes with the configured password;
an existing volume retains its old password until explicitly rotated.

The Docker build receives only the backend Python source, migrations and dependency
inputs. `.env`, frontend secrets, Git history, runtime data, caches and logs are
excluded from the context; credentials are not build arguments or image ENV values.
Runtime environment credentials remain visible to the local process owner and
Docker administrators. This is a private local configuration, not a production
secret-management or deployment design. The existing local database role remains
an administrative development role; production privileges need a separate review.

## Before publishing

- Keep `.env.example` credential fields empty. Only that root template is exempt
  from environment-file ignore rules.
- Check `git status --short`, `git diff --cached --stat` and the staged file list.
- Use `git check-ignore` for real/nested environment files, Streamlit secrets,
  private keys, local databases, model caches and logs. Never force-add them.
- Run Gitleaks with full redaction over all history and the staged/public tree.
  Keep raw audit evidence under ignored `data/evidence/security/`.
- If a real credential is found in history, stop publication, rotate/revoke it,
  and plan history remediation. Deleting the current file is insufficient. Do not
  rewrite shared history or force-push without explicit authorization.

The checked behavior follows the official [python-dotenv documentation](https://bbc2.github.io/python-dotenv/),
[Compose interpolation documentation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)
and [PostgreSQL environment-variable documentation](https://www.postgresql.org/docs/16/libpq-envars.html).
