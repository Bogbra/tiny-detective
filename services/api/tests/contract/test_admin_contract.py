def test_admin_endpoint_disabled_when_token_not_configured(client, monkeypatch):
    monkeypatch.delenv("ADMIN_API_TOKEN", raising=False)

    response = client.post("/admin/cases/case_bakesale_001/approve", headers={"X-Admin-Token": "anything"})

    assert response.status_code == 401


def test_admin_endpoint_rejects_wrong_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "secret")

    response = client.post("/admin/cases/case_bakesale_001/approve", headers={"X-Admin-Token": "wrong"})

    assert response.status_code == 401


def test_admin_endpoint_accepts_correct_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "secret")

    response = client.post("/admin/cases/case_bakesale_001/approve", headers={"X-Admin-Token": "secret"})

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_reject_case(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "secret")

    response = client.post("/admin/cases/case_bakesale_001/reject", headers={"X-Admin-Token": "secret"})

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_publish_daily_rejects_non_approved_case(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "secret")

    response = client.post(
        "/admin/cases/case_bakesale_001/publish-daily", headers={"X-Admin-Token": "secret"}
    )

    assert response.status_code == 409


def test_publish_daily_rejects_unknown_case(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "secret")

    response = client.post("/admin/cases/does-not-exist/publish-daily", headers={"X-Admin-Token": "secret"})

    assert response.status_code == 404


def test_approve_then_publish_daily_succeeds(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "secret")
    headers = {"X-Admin-Token": "secret"}

    approve = client.post("/admin/cases/case_bakesale_001/approve", headers=headers)
    assert approve.status_code == 200

    publish = client.post("/admin/cases/case_bakesale_001/publish-daily", headers=headers)
    assert publish.status_code == 200

    daily = client.get("/cases/daily")
    assert daily.status_code == 200
    assert daily.json()["caseId"] == "case_bakesale_001"


def test_publish_next_daily_requires_admin_token(client):
    response = client.post("/admin/cases/publish-next-daily")

    assert response.status_code == 401


def test_publish_next_daily_publishes_the_only_eligible_seed_case(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "secret")
    headers = {"X-Admin-Token": "secret"}

    # Only case_museum_001 starts APPROVED in seed_cases(); case_bakesale_001
    # starts DRAFT, so it's not yet eligible for the scheduler to pick.
    response = client.post("/admin/cases/publish-next-daily", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"caseId": "case_museum_001", "status": "live"}

    daily = client.get("/cases/daily")
    assert daily.json()["caseId"] == "case_museum_001"


def test_publish_next_daily_returns_409_when_catalog_is_empty(client, monkeypatch):
    # case_museum_001 (APPROVED) is permanently eligible with no existing
    # admin endpoint to un-approve it, so an empty catalog isn't reachable
    # through seed data + the public admin API alone — swap in a genuinely
    # empty repository instead, the same way an emptied production
    # Firestore `cases` collection would look to this endpoint.
    from app.api import dependencies
    from app.infrastructure.repositories.in_memory_case_repository import InMemoryCaseRepository
    from app.main import app

    monkeypatch.setenv("ADMIN_API_TOKEN", "secret")
    app.dependency_overrides[dependencies.get_case_repository] = lambda: InMemoryCaseRepository()

    response = client.post("/admin/cases/publish-next-daily", headers={"X-Admin-Token": "secret"})

    assert response.status_code == 409


def test_publish_next_daily_rotates_away_from_todays_case(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "secret")
    headers = {"X-Admin-Token": "secret"}

    client.post("/admin/cases/case_bakesale_001/approve", headers=headers)
    first = client.post("/admin/cases/publish-next-daily", headers=headers)
    assert first.json()["caseId"] == "case_museum_001"

    second = client.post("/admin/cases/publish-next-daily", headers=headers)
    assert second.json()["caseId"] == "case_bakesale_001"
