def test_public_case_hides_solution_and_private_fields(client):
    response = client.get("/cases/case_museum_001")

    assert response.status_code == 200
    body = response.json()
    assert "solution" not in body
    for suspect in body["suspects"]:
        assert "isCulprit" not in suspect
        assert "privateReasoning" not in suspect
    for clue in body["clues"]:
        assert set(clue.keys()) == {"clueId", "text"}


def test_unknown_case_returns_404(client):
    response = client.get("/cases/does-not-exist")

    assert response.status_code == 404


def test_draft_case_is_not_publicly_visible(client):
    response = client.get("/cases/case_bakesale_001")

    assert response.status_code == 404


def test_daily_case_404_before_publish(client):
    response = client.get("/cases/daily")

    assert response.status_code == 404


def test_daily_case_available_after_publish(client, monkeypatch):
    monkeypatch.setenv("ADMIN_API_TOKEN", "test-token")
    headers = {"X-Admin-Token": "test-token"}

    publish = client.post("/admin/cases/case_museum_001/publish-daily", headers=headers)
    assert publish.status_code == 200

    response = client.get("/cases/daily")
    assert response.status_code == 200
    assert response.json()["caseId"] == "case_museum_001"


def test_daily_route_is_not_shadowed_by_case_id_route(client, monkeypatch):
    """Route-ordering guard.

    GET /cases/daily and GET /cases/{case_id} are declared on the same
    router. If /cases/{case_id} were ever registered before /cases/daily,
    FastAPI would match "daily" as a case_id and this would 404 with a body
    like {"detail": "case 'daily' not found"} instead of returning the
    published case — a silent regression a generic 404 assertion elsewhere
    wouldn't distinguish from "no daily case published yet". This test fails
    loudly and specifically if that ordering ever regresses.
    """
    monkeypatch.setenv("ADMIN_API_TOKEN", "test-token")
    headers = {"X-Admin-Token": "test-token"}

    publish = client.post("/admin/cases/case_museum_001/publish-daily", headers=headers)
    assert publish.status_code == 200

    response = client.get("/cases/daily")

    assert response.status_code == 200
    assert "'daily'" not in response.text
    assert response.json()["caseId"] == "case_museum_001"
