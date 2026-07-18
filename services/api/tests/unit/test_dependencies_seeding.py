from app.api.dependencies import _should_seed_demo_cases


def test_does_not_seed_when_neither_env_var_is_set(monkeypatch):
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    assert _should_seed_demo_cases() is False


def test_seeds_when_emulator_host_is_set(monkeypatch):
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "localhost:8080")
    assert _should_seed_demo_cases() is True


def test_does_not_seed_in_production_shape_project_set_without_emulator(monkeypatch):
    """The real production env var shape (see ADR-0006's deploy.yml):
    GOOGLE_CLOUD_PROJECT is set, FIRESTORE_EMULATOR_HOST is not. Seeding
    must stay off here — this is exactly the case task 8 of the
    security/ops audit closes: a freshly-provisioned or accidentally-wiped
    production database must not get silently auto-populated with demo
    content."""
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "tiny-detective-ai")
    assert _should_seed_demo_cases() is False


def test_seeds_when_both_env_vars_are_set(monkeypatch):
    # A local dev setup pointed at the emulator often also has
    # GOOGLE_CLOUD_PROJECT set (matching firestore_client.py's project
    # param) — the emulator host being present is still what decides it.
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "localhost:8080")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "tiny-detective-dev")
    assert _should_seed_demo_cases() is True


def test_empty_emulator_host_does_not_seed(monkeypatch):
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "")
    assert _should_seed_demo_cases() is False
