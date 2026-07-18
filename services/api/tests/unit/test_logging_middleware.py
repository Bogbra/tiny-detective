import logging

import pytest
from fastapi import Request

from app.api.logging_middleware import _trace_resource_name, logging_middleware


def _make_request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
        "headers": raw_headers,
        "client": ("10.0.0.1", 12345),
    }
    return Request(scope)


def test_returns_none_when_header_absent(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "tiny-detective-ai")
    request = _make_request()
    assert _trace_resource_name(request) is None


def test_returns_none_when_project_env_var_unset(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    request = _make_request({"x-cloud-trace-context": "abc123/456;o=1"})
    assert _trace_resource_name(request) is None


def test_builds_full_resource_name(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "tiny-detective-ai")
    request = _make_request({"x-cloud-trace-context": "105445aa7843bc8bf206b120001000/1;o=1"})
    assert _trace_resource_name(request) == "projects/tiny-detective-ai/traces/105445aa7843bc8bf206b120001000"


def test_handles_header_with_no_slash(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "tiny-detective-ai")
    request = _make_request({"x-cloud-trace-context": "justatraceid"})
    assert _trace_resource_name(request) == "projects/tiny-detective-ai/traces/justatraceid"


def test_empty_header_returns_none(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "tiny-detective-ai")
    request = _make_request({"x-cloud-trace-context": ""})
    assert _trace_resource_name(request) is None


@pytest.mark.anyio
async def test_unhandled_exception_is_logged_with_error_severity_and_reraised(caplog):
    """Closes task 12's real gap: without this, an unhandled exception
    never reaches our own logger at all, only a bare stderr traceback --
    meaning it would never get a guaranteed severity: ERROR + exception
    field for Cloud Error Reporting to pick up."""
    request = _make_request()

    async def _call_next_raises(_request):
        raise ValueError("boom")

    with caplog.at_level(logging.ERROR, logger="app.access"):
        with pytest.raises(ValueError, match="boom"):
            await logging_middleware(request, _call_next_raises)

    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_records) == 1
    assert error_records[0].exc_info is not None
    assert "unhandled exception" in error_records[0].getMessage()


@pytest.mark.anyio
async def test_successful_request_is_logged_at_info_not_error(caplog):
    request = _make_request()

    class _Response:
        status_code = 200

    async def _call_next_ok(_request):
        return _Response()

    with caplog.at_level(logging.INFO, logger="app.access"):
        response = await logging_middleware(request, _call_next_ok)

    assert response.status_code == 200
    assert all(r.levelno == logging.INFO for r in caplog.records)
