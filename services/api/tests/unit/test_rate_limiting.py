from fastapi import Request

from app.api.rate_limiting import TRUSTED_PROXY_HOPS_ENV_VAR, _client_ip


def _make_request(headers: dict[str, str] | None = None, client_host: str = "10.0.0.1") -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope = {"type": "http", "headers": raw_headers, "client": (client_host, 12345)}
    return Request(scope)


def test_absent_header_falls_back_to_socket_peer_address():
    request = _make_request(client_host="192.168.1.1")
    assert _client_ip(request) == "192.168.1.1"


def test_single_entry_xff_is_used_directly():
    request = _make_request({"x-forwarded-for": "203.0.113.5"})
    assert _client_ip(request) == "203.0.113.5"


def test_spoofed_multi_entry_xff_resolves_to_the_cloud_run_appended_ip():
    # An attacker can prepend anything before Cloud Run's own hop, but
    # cannot forge what Cloud Run itself appends at the end. With the
    # default trust of 1 hop, only the LAST entry is trustworthy.
    request = _make_request({"x-forwarded-for": "9.9.9.9, 8.8.8.8, 203.0.113.5"})
    assert _client_ip(request) == "203.0.113.5"


def test_first_entry_alone_no_longer_wins_regression_guard():
    request = _make_request({"x-forwarded-for": "1.2.3.4, 5.6.7.8"})
    ip = _client_ip(request)
    assert ip != "1.2.3.4"
    assert ip == "5.6.7.8"


def test_two_trusted_hops_uses_second_to_last_entry(monkeypatch):
    monkeypatch.setenv(TRUSTED_PROXY_HOPS_ENV_VAR, "2")
    request = _make_request({"x-forwarded-for": "9.9.9.9, 203.0.113.5, 10.10.10.10"})
    assert _client_ip(request) == "203.0.113.5"


def test_trusted_hops_clamped_to_available_entries(monkeypatch):
    # Header has fewer entries than the configured trusted-hop count —
    # take the earliest available entry rather than raising an IndexError.
    monkeypatch.setenv(TRUSTED_PROXY_HOPS_ENV_VAR, "5")
    request = _make_request({"x-forwarded-for": "203.0.113.5, 10.10.10.10"})
    assert _client_ip(request) == "203.0.113.5"


def test_invalid_trusted_hops_env_falls_back_to_default(monkeypatch):
    monkeypatch.setenv(TRUSTED_PROXY_HOPS_ENV_VAR, "not-a-number")
    request = _make_request({"x-forwarded-for": "9.9.9.9, 203.0.113.5"})
    assert _client_ip(request) == "203.0.113.5"


def test_zero_or_negative_trusted_hops_falls_back_to_default(monkeypatch):
    monkeypatch.setenv(TRUSTED_PROXY_HOPS_ENV_VAR, "0")
    request = _make_request({"x-forwarded-for": "9.9.9.9, 203.0.113.5"})
    assert _client_ip(request) == "203.0.113.5"


def test_whitespace_and_empty_entries_are_ignored():
    request = _make_request({"x-forwarded-for": "9.9.9.9,  , 203.0.113.5 ,"})
    assert _client_ip(request) == "203.0.113.5"


def test_empty_header_falls_back_to_socket_peer_address():
    request = _make_request({"x-forwarded-for": ""}, client_host="192.168.1.1")
    assert _client_ip(request) == "192.168.1.1"
