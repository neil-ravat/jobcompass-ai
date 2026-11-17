FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.0 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --extra postgres --extra semantic
COPY jobcompass ./jobcompass
COPY migrations ./migrations
ENV PATH="/app/.venv/bin:$PATH" JOBCOMPASS_DATA_DIR=/app/data JOBCOMPASS_MODEL_CACHE=/app/data/models
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "jobcompass.api:app", "--host", "0.0.0.0", "--port", "8000"]
