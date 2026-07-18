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
