from fastapi import Request

from app.api.logging_middleware import _trace_resource_name


def _make_request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {"type": "http", "headers": raw_headers, "client": ("10.0.0.1", 12345)}
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
    assert (
        _trace_resource_name(request)
        == "projects/tiny-detective-ai/traces/105445aa7843bc8bf206b120001000"
    )


def test_handles_header_with_no_slash(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "tiny-detective-ai")
    request = _make_request({"x-cloud-trace-context": "justatraceid"})
    assert _trace_resource_name(request) == "projects/tiny-detective-ai/traces/justatraceid"


def test_empty_header_returns_none(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "tiny-detective-ai")
    request = _make_request({"x-cloud-trace-context": ""})
    assert _trace_resource_name(request) is None
