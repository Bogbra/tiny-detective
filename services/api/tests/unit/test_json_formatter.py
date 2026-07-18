import json
import logging

from app.infrastructure.logging.json_formatter import JsonFormatter
from app.infrastructure.logging.request_context import set_trace_id


def _make_record(msg="hello", level=logging.INFO, extra=None) -> logging.LogRecord:
    record = logging.LogRecord(
        name="app.test", level=level, pathname=__file__, lineno=1, msg=msg, args=(), exc_info=None
    )
    for key, value in (extra or {}).items():
        setattr(record, key, value)
    return record


def test_formats_basic_fields_as_json():
    set_trace_id(None)
    record = _make_record("something happened")
    payload = json.loads(JsonFormatter().format(record))

    assert payload["severity"] == "INFO"
    assert payload["message"] == "something happened"
    assert payload["logger"] == "app.test"


def test_omits_trace_field_when_no_trace_set():
    set_trace_id(None)
    payload = json.loads(JsonFormatter().format(_make_record()))
    assert "logging.googleapis.com/trace" not in payload


def test_includes_trace_field_when_set():
    set_trace_id("projects/tiny-detective-ai/traces/abc123")
    try:
        payload = json.loads(JsonFormatter().format(_make_record()))
        assert payload["logging.googleapis.com/trace"] == "projects/tiny-detective-ai/traces/abc123"
    finally:
        set_trace_id(None)


def test_error_severity_maps_through():
    record = _make_record("boom", level=logging.ERROR)
    payload = json.loads(JsonFormatter().format(record))
    assert payload["severity"] == "ERROR"


def test_extra_fields_are_surfaced_as_structured_attributes():
    record = _make_record("case generated", extra={"caseGeneration": {"outcome": "saved", "costUsd": 0.0007}})
    payload = json.loads(JsonFormatter().format(record))
    assert payload["caseGeneration"] == {"outcome": "saved", "costUsd": 0.0007}


def test_exception_info_is_included():
    try:
        raise ValueError("bad input")
    except ValueError:
        import sys

        record = logging.LogRecord(
            name="app.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="failed",
            args=(),
            exc_info=sys.exc_info(),
        )
    payload = json.loads(JsonFormatter().format(record))
    assert "ValueError" in payload["exception"]
    assert "bad input" in payload["exception"]


def test_output_is_a_single_json_line_no_embedded_newlines():
    # Cloud Logging parses one JSON object per line — a multi-line message
    # (e.g. a formatted traceback) must not break that.
    record = _make_record("line one\nline two")
    formatted = JsonFormatter().format(record)
    assert "\n" not in formatted
    payload = json.loads(formatted)
    assert payload["message"] == "line one\nline two"
