"""Per-request structured access logging + Cloud Trace correlation.

Parses X-Cloud-Trace-Context (the header Cloud Run's load balancer sets on
every incoming request: "TRACE_ID/SPAN_ID;o=TRACE_TRUE") into the full
`projects/{project}/traces/{TRACE_ID}` resource name Cloud Logging expects
for its `logging.googleapis.com/trace` field, and stores it in a
request-scoped contextvar (app.infrastructure.logging.request_context)
before the route handler runs — so every log line emitted anywhere during
this request's handling, not just this middleware's own access-log line,
gets attributed to the right trace and groups together in Cloud Logging's
"show request logs" view.
"""

import logging
import os
import time

from fastapi import Request

from app.infrastructure.logging.request_context import set_trace_id

logger = logging.getLogger("app.access")


def _trace_resource_name(request: Request) -> str | None:
    header = request.headers.get("x-cloud-trace-context", "")
    if not header:
        return None
    trace_id = header.split("/", 1)[0].strip()
    if not trace_id:
        return None
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        # Local dev / no project configured — nothing to correlate
        # against; the bare trace id alone isn't a valid resource name.
        return None
    return f"projects/{project}/traces/{trace_id}"


async def logging_middleware(request: Request, call_next):
    set_trace_id(_trace_resource_name(request))

    start = time.monotonic()
    response = await call_next(request)
    latency_ms = (time.monotonic() - start) * 1000

    logger.info(
        "%s %s -> %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
        extra={
            "httpRequest": {
                "requestMethod": request.method,
                "requestUrl": str(request.url),
                "status": response.status_code,
                "latency": f"{latency_ms / 1000:.3f}s",
            }
        },
    )
    return response
