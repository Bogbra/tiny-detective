def test_hint_limit_enforced(client):
    player = client.post("/players").json()
    player_id = player["playerId"]

    for _ in range(3):
        response = client.post("/cases/case_museum_001/hint", json={"playerId": player_id})
        assert response.status_code == 200

    fourth = client.post("/cases/case_museum_001/hint", json={"playerId": player_id})
    assert fourth.status_code == 409


def test_hint_response_shape(client):
    player = client.post("/players").json()

    response = client.post(
        "/cases/case_museum_001/hint", json={"playerId": player["playerId"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["hintsUsed"] == 1
    assert body["hintsRemaining"] == 2
    assert body["text"]


def test_hint_for_unknown_case_returns_404(client):
    player = client.post("/players").json()

    response = client.post(
        "/cases/does-not-exist/hint", json={"playerId": player["playerId"]}
    )

    assert response.status_code == 404


def test_hint_endpoint_rate_limits_by_caller(client):
    """5/minute per caller (app/api/rate_limiting.py), independent of the
    domain-level per-case hint limit (HintPolicy, tested above) — a
    different player each time keeps every individual request under that
    domain limit, isolating this test to the rate limiter specifically."""
    for _ in range(5):
        player = client.post("/players").json()
        response = client.post(
            "/cases/case_museum_001/hint", json={"playerId": player["playerId"]}
        )
        assert response.status_code == 200

    sixth_player = client.post("/players").json()
    sixth = client.post(
        "/cases/case_museum_001/hint", json={"playerId": sixth_player["playerId"]}
    )
    assert sixth.status_code == 429


def test_hints_used_reduce_score(client):
    player = client.post("/players").json()
    player_id = player["playerId"]

    client.post("/cases/case_museum_001/hint", json={"playerId": player_id})
    client.post("/cases/case_museum_001/hint", json={"playerId": player_id})

    response = client.post(
        "/cases/case_museum_001/solution",
        json={"playerId": player_id, "suspectId": "suspect_3"},
    )

    assert response.json()["score"] == 70
