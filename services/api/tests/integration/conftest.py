"""Real-Firestore-emulator integration tests.

These construct their own FirestoreCaseRepository/etc. with their own
client, bypassing the app's dependency-injection singletons entirely (which
always pick in-memory during pytest — see
app.infrastructure.firestore.firestore_client.is_firestore_configured).
That's deliberate: this is where Firestore is actually meant to be
exercised for real.

Gracefully skipped as a whole module if the emulator isn't reachable, so
`uv run pytest` stays green on a machine without Docker running. Start it
with:

    docker run -d -p 8080:8080 gcr.io/google.com/cloudsdktool/cloud-sdk:emulators \\
      gcloud emulators firestore start --host-port=0.0.0.0:8080
"""

import os
import socket

import pytest

from app.infrastructure.firestore.firestore_client import get_firestore_client


def _emulator_reachable() -> bool:
    """A raw TCP probe with a short, explicit timeout — deliberately NOT a
    real Firestore client call. The google-cloud-firestore/gRPC client's own
    connection-failure behavior against a closed port was measured to hang
    (not fail fast) when the emulator container had stopped, which would
    make the whole test suite hang instead of skipping. A plain socket
    connect either succeeds or raises within `timeout` seconds, no gRPC
    retry/backoff involved.
    """
    host_port = os.environ.get("FIRESTORE_EMULATOR_HOST")
    if not host_port:
        return False
    host, _, port_str = host_port.partition(":")
    try:
        port = int(port_str)
    except ValueError:
        return False
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


requires_firestore_emulator = pytest.mark.skipif(
    not _emulator_reachable(),
    reason=(
        "FIRESTORE_EMULATOR_HOST not set or the emulator isn't reachable. "
        "Start it with: docker run -d -p 8080:8080 "
        "gcr.io/google.com/cloudsdktool/cloud-sdk:emulators "
        "gcloud emulators firestore start --host-port=0.0.0.0:8080"
    ),
)

_TOUCHED_COLLECTIONS = [
    "cases",
    "daily_cases",
    "players",
    "hint_requests",
    "case_attempts",
    "rate_limits",
]


@pytest.fixture
def firestore_client():
    return get_firestore_client()


@pytest.fixture(autouse=True)
def _clean_firestore_collections(firestore_client):
    """The emulator persists data across test runs (unlike the in-memory
    repositories, which reset per process) — clear before AND after each
    test so tests don't see leftovers from a previous run or leave any
    behind for the next one."""

    def _clear() -> None:
        for name in _TOUCHED_COLLECTIONS:
            for doc in firestore_client.collection(name).stream():
                doc.reference.delete()

    _clear()
    yield
    _clear()
