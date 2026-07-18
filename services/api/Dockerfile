FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Build context is the repo root, not services/api (see the docker-build CI
# job / deploy.yml) — the live case-generation feature (ADR-0007) makes
# services/api depend on tools/ai-content as a uv editable path dependency
# (../../tools/ai-content, relative to services/api/pyproject.toml), so
# both directories need to exist in the image at the same relative
# structure they have in the repo for that path to resolve.
COPY tools/ai-content ./tools/ai-content
COPY services/api/pyproject.toml services/api/uv.lock ./services/api/

WORKDIR /app/services/api
RUN uv sync --frozen --no-dev

COPY services/api/app ./app

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
