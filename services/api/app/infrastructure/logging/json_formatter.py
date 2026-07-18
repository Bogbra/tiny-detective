"""Cloud-Logging-compatible JSON log formatter.

Without this, Cloud Run/Cloud Logging receives plain text lines and maps
every one of them to severity "Default" — no way to filter by ERROR in the
console, no automatic correlation with the request that produced them, and
(via task 12's Error Reporting integration) no automatic error grouping,
since that requires a real `severity: ERROR` field plus a stack trace in
the JSON payload, not text Cloud Logging has to guess at.

Deliberately stdlib logging + this one small formatter, not a logging
framework (structlog, python-json-logger, etc.) — the actual requirement
(map Python's levelname to Cloud Logging's `severity` field, attach a
trace id, pass through `extra=` fields as structured attributes) is small
enough that a dependency isn't earning its keep at this project's scale.
"""

import json
import logging

from .request_context import get_trace_id

# Python's levelnames already match Cloud Logging's severity enum values
# for every level this project actually uses (INFO/WARNING/ERROR/CRITICAL/
# DEBUG) — no translation table needed, just pass the levelname through.
_STANDARD_RECORD_ATTRS = frozenset(vars(logging.LogRecord("", 0, "", 0, "", (), None)).keys()) | {
    "message",
    "asctime",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        trace_id = get_trace_id()
        if trace_id:
            payload["logging.googleapis.com/trace"] = trace_id

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Anything passed via logging.info(..., extra={...}) becomes a
        # regular attribute on the LogRecord — surface it as a structured
        # field rather than requiring it to be pre-formatted into the
        # message string. See generate_case.py's _log_usage for the
        # motivating case (real per-request token/cost data).
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS and key not in payload:
                payload[key] = value

        return json.dumps(payload, default=str)
