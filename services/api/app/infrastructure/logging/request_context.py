"""Request-scoped trace-id storage, read by JsonFormatter to attach
Cloud Logging's `logging.googleapis.com/trace` field to every log record
emitted while handling a given request — including ones emitted several
layers deep in application/domain code that has no idea an HTTP request is
in flight (e.g. generate_case.py's cost logging).

A plain contextvars.ContextVar, not a global/thread-local: it needs to be
per-async-task (one value per concurrent request on the same event loop),
which only contextvars actually guarantees. Set once, at the top of
app.api.logging_middleware, before the route handler runs; correctly
propagates through both async awaits and Starlette's run_in_threadpool
(anyio copies the current Context into the worker thread), so sync routes
running in the threadpool see it too.
"""

import contextvars

_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("trace_id", default=None)


def set_trace_id(trace_id: str | None) -> None:
    _trace_id.set(trace_id)


def get_trace_id() -> str | None:
    return _trace_id.get()
