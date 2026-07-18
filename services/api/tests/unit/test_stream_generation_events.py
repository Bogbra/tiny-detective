import asyncio

import pytest

from app.api.routes.cases import stream_generation_events
from app.application.use_cases.generate_case import GenerationEvent


async def _collect(events: list[GenerationEvent], *, heartbeat_seconds: float) -> list[str]:
    async def _events():
        for event in events:
            yield event

    return [chunk async for chunk in stream_generation_events(_events(), heartbeat_seconds=heartbeat_seconds)]


@pytest.mark.anyio
async def test_no_heartbeat_when_events_arrive_promptly():
    events = [GenerationEvent(step="generating", status="running", attempt=1)]
    chunks = await _collect(events, heartbeat_seconds=5)

    assert len(chunks) == 1
    assert chunks[0].startswith("data: ")
    assert "keep-alive" not in chunks[0]


@pytest.mark.anyio
async def test_heartbeat_emitted_while_waiting_for_a_slow_event():
    """The real gap this closes: a slow attempt (a real OpenAI call, up to
    30s — see openai_client.py's timeout, task 6) must not leave the SSE
    connection silent long enough for an intermediary to kill it as idle.
    A tiny heartbeat_seconds makes this fast and deterministic to test —
    the actual production interval (15s) is a separate, unit-tested
    constant, not re-derived here."""

    async def _slow_then_fast_events():
        await asyncio.sleep(0.2)
        yield GenerationEvent(step="generating", status="passed", attempt=1)

    chunks = [
        chunk async for chunk in stream_generation_events(_slow_then_fast_events(), heartbeat_seconds=0.05)
    ]

    heartbeats = [c for c in chunks if c == ": keep-alive\n\n"]
    data_events = [c for c in chunks if c.startswith("data: ")]

    assert len(heartbeats) >= 2  # 0.2s / 0.05s heartbeat should fire multiple times
    assert len(data_events) == 1
    # The real event must come last — heartbeats are filler, not a
    # replacement for the actual event once it's ready.
    assert chunks[-1] == data_events[0]


@pytest.mark.anyio
async def test_heartbeat_lines_are_valid_sse_comments():
    async def _slow_events():
        await asyncio.sleep(0.1)
        yield GenerationEvent(step="failed", status="done", detail="timed out")

    chunks = [chunk async for chunk in stream_generation_events(_slow_events(), heartbeat_seconds=0.02)]

    heartbeats = [c for c in chunks if "keep-alive" in c]
    assert heartbeats
    for heartbeat in heartbeats:
        # SSE comments start with ":" and end with a blank line (\n\n) —
        # any real event-stream consumer (including the browser's own
        # EventSource, even though this app doesn't use it) ignores lines
        # shaped like this.
        assert heartbeat.startswith(":")
        assert heartbeat.endswith("\n\n")


@pytest.mark.anyio
async def test_stream_ends_cleanly_with_no_trailing_heartbeat_after_the_last_event():
    events = [GenerationEvent(step="failed", status="done", detail="could not generate a valid case")]
    chunks = await _collect(events, heartbeat_seconds=5)

    assert chunks[-1].startswith("data: ")
    assert not any("keep-alive" in c for c in chunks)
