import pytest

from app.infrastructure.auth import scheduler_oidc

_SCHEDULER_EMAIL = "scheduler@tiny-detective-ai.iam.gserviceaccount.com"
_AUDIENCE = "https://tiny-detective-api.example/admin/cases/publish-next-daily"


@pytest.fixture(autouse=True)
def _configured_env(monkeypatch):
    monkeypatch.setenv(scheduler_oidc.SCHEDULER_SERVICE_ACCOUNT_EMAIL_ENV_VAR, _SCHEDULER_EMAIL)
    monkeypatch.setenv(scheduler_oidc.SCHEDULER_OIDC_AUDIENCE_ENV_VAR, _AUDIENCE)


def test_accepts_a_token_from_the_expected_service_account(monkeypatch):
    monkeypatch.setattr(
        scheduler_oidc.id_token,
        "verify_oauth2_token",
        lambda *a, **k: {
            "email": _SCHEDULER_EMAIL,
            "email_verified": True,
        },
    )

    assert scheduler_oidc.verify_scheduler_oidc_token("valid-token") is True


def test_rejects_a_token_from_a_different_service_account(monkeypatch):
    monkeypatch.setattr(
        scheduler_oidc.id_token,
        "verify_oauth2_token",
        lambda *a, **k: {"email": "someone-else@example.com", "email_verified": True},
    )

    assert scheduler_oidc.verify_scheduler_oidc_token("valid-but-wrong-identity") is False


def test_rejects_when_email_is_not_verified(monkeypatch):
    monkeypatch.setattr(
        scheduler_oidc.id_token,
        "verify_oauth2_token",
        lambda *a, **k: {
            "email": _SCHEDULER_EMAIL,
            "email_verified": False,
        },
    )

    assert scheduler_oidc.verify_scheduler_oidc_token("unverified-email-token") is False


def test_rejects_an_invalid_or_expired_token(monkeypatch):
    from google.auth.exceptions import GoogleAuthError

    def _raise(*args, **kwargs):
        raise GoogleAuthError("token expired")

    monkeypatch.setattr(scheduler_oidc.id_token, "verify_oauth2_token", _raise)

    assert scheduler_oidc.verify_scheduler_oidc_token("expired-token") is False


def test_rejects_malformed_token_input(monkeypatch):
    def _raise(*args, **kwargs):
        raise ValueError("not a valid JWT")

    monkeypatch.setattr(scheduler_oidc.id_token, "verify_oauth2_token", _raise)

    assert scheduler_oidc.verify_scheduler_oidc_token("not-a-jwt") is False


def test_fails_closed_when_service_account_env_var_is_unset(monkeypatch):
    monkeypatch.delenv(scheduler_oidc.SCHEDULER_SERVICE_ACCOUNT_EMAIL_ENV_VAR, raising=False)

    assert scheduler_oidc.verify_scheduler_oidc_token("anything") is False


def test_fails_closed_when_audience_env_var_is_unset(monkeypatch):
    monkeypatch.delenv(scheduler_oidc.SCHEDULER_OIDC_AUDIENCE_ENV_VAR, raising=False)

    assert scheduler_oidc.verify_scheduler_oidc_token("anything") is False
