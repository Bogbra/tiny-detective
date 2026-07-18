from ai_content.openai_client import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_RETRIES_ENV_VAR,
    TIMEOUT_ENV_VAR,
    _max_retries,
    _timeout_seconds,
)


def test_timeout_defaults_when_env_unset(monkeypatch):
    monkeypatch.delenv(TIMEOUT_ENV_VAR, raising=False)
    assert _timeout_seconds() == DEFAULT_TIMEOUT_SECONDS


def test_timeout_reads_env_override(monkeypatch):
    monkeypatch.setenv(TIMEOUT_ENV_VAR, "10")
    assert _timeout_seconds() == 10.0


def test_timeout_falls_back_to_default_on_invalid_value(monkeypatch):
    monkeypatch.setenv(TIMEOUT_ENV_VAR, "not-a-number")
    assert _timeout_seconds() == DEFAULT_TIMEOUT_SECONDS


def test_timeout_falls_back_to_default_on_non_positive_value(monkeypatch):
    monkeypatch.setenv(TIMEOUT_ENV_VAR, "0")
    assert _timeout_seconds() == DEFAULT_TIMEOUT_SECONDS


def test_max_retries_defaults_when_env_unset(monkeypatch):
    monkeypatch.delenv(MAX_RETRIES_ENV_VAR, raising=False)
    assert _max_retries() == DEFAULT_MAX_RETRIES


def test_max_retries_reads_env_override(monkeypatch):
    monkeypatch.setenv(MAX_RETRIES_ENV_VAR, "3")
    assert _max_retries() == 3


def test_max_retries_zero_is_respected(monkeypatch):
    monkeypatch.setenv(MAX_RETRIES_ENV_VAR, "0")
    assert _max_retries() == 0


def test_max_retries_falls_back_to_default_on_invalid_value(monkeypatch):
    monkeypatch.setenv(MAX_RETRIES_ENV_VAR, "not-a-number")
    assert _max_retries() == DEFAULT_MAX_RETRIES
