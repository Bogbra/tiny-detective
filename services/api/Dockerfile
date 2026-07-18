# Pinned by digest, not just the "3.12-slim" tag — a tag can be
# repointed to a different image at any time (a base-image update landing
# silently on the next unrelated build, with no diff to review); a digest
# is content-addressed and can only ever resolve to this exact image.
# Re-pin deliberately (docker pull python:3.12-slim && docker inspect
# --format='{{index .RepoDigests 0}}' python:3.12-slim) when a base-image
# update is actually wanted, not automatically.
FROM python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de

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

# Runs as a non-root user, not the container default root — limits the
# blast radius of a container-escape/RCE-class vulnerability to whatever
# this specific unprivileged user can touch, rather than the whole
# container. No chown needed: everything above this point (.venv, app
# code) was built/copied as root but only ever needs to be read and
# executed from here on, never written to at runtime — default
# world-readable/executable permissions on files root creates are enough.
RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser

EXPOSE 8080

# Invokes the already-built venv's own uvicorn binary directly, not
# `uv run uvicorn ...` — `uv run` re-verifies the environment against
# pyproject.toml/uv.lock on every invocation and, for the editable
# tools/ai-content dependency, attempts to rebuild it (touching its
# egg-info directory) if it thinks anything changed. That rebuild attempt
# is exactly what broke this Dockerfile change on the first real test: it
# needs write access appuser doesn't have (correctly, this image should
# never need to write into itself at runtime). The venv `uv sync` already
# built is complete and correct; running its uvicorn directly skips a
# check meant for local development, not an immutable built image.
CMD ["/app/services/api/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
