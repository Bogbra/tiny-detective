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

    response = client.post("/cases/case_museum_001/hint", json={"playerId": player["playerId"]})

    assert response.status_code == 200
    body = response.json()
    assert body["hintsUsed"] == 1
    assert body["hintsRemaining"] == 2
    assert body["text"]


def test_hint_rejects_oversized_player_id(client):
    response = client.post("/cases/case_museum_001/hint", json={"playerId": "p" * 65})
    assert response.status_code == 422


def test_hint_rejects_player_id_with_invalid_characters(client):
    response = client.post("/cases/case_museum_001/hint", json={"playerId": "../etc/passwd"})
    assert response.status_code == 422


def test_hint_for_unregistered_player_returns_404(client):
    """Closes the hint-limit bypass: a random UUID that was never POSTed to
    /players must not get its own fresh hint budget just by being used as
    playerId — see task 2 of the security/ops audit."""
    response = client.post("/cases/case_museum_001/hint", json={"playerId": "never-registered-player-id"})

    assert response.status_code == 404


def test_hint_for_unknown_case_returns_404(client):
    player = client.post("/players").json()

    response = client.post("/cases/does-not-exist/hint", json={"playerId": player["playerId"]})

    assert response.status_code == 404


def test_hint_endpoint_rate_limits_by_caller(client):
    """5/minute per caller (app/api/rate_limiting.py), independent of the
    domain-level per-case hint limit (HintPolicy, tested above) — a
    different player each time keeps every individual request under that
    domain limit, isolating this test to the rate limiter specifically.

    Pre-creates all 6 players up front, then resets the shared limiter
    before exercising /hint: POST /players has its own, separate,
    much-lower limit (see rate_limiting.py's per_instance_limit — divided
    for instance-count-awareness per task 5 of the security/ops audit),
    which would otherwise be exhausted by this test's own setup before ever
    reaching the /hint assertions this test is actually about.
    """
    from app.api.rate_limiting import limiter

    player_ids = []
    for _ in range(6):
        # Reset before each creation too — POST /players' own limit (4)
        # is lower than the 6 we need here, and this test has nothing to
        # do with that endpoint's limit specifically.
        limiter.reset()
        player_ids.append(client.post("/players").json()["playerId"])
    limiter.reset()

    for player_id in player_ids[:5]:
        response = client.post("/cases/case_museum_001/hint", json={"playerId": player_id})
        assert response.status_code == 200

    sixth = client.post("/cases/case_museum_001/hint", json={"playerId": player_ids[5]})
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
