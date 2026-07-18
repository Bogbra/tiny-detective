def test_submit_correct_solution(client):
    player = client.post("/players").json()

    response = client.post(
        "/cases/case_museum_001/solution",
        json={"playerId": player["playerId"], "suspectId": "suspect_3"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is True
    assert body["score"] == 100
    assert body["streak"] == 1
    assert body["solutionExplanation"]


def test_submit_incorrect_solution(client):
    player = client.post("/players").json()

    response = client.post(
        "/cases/case_museum_001/solution",
        json={"playerId": player["playerId"], "suspectId": "suspect_1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["correct"] is False
    assert body["score"] == 0
    assert body["streak"] == 0


def test_submit_solution_rejects_oversized_player_id(client):
    response = client.post(
        "/cases/case_museum_001/solution",
        json={"playerId": "p" * 65, "suspectId": "suspect_1"},
    )
    assert response.status_code == 422


def test_submit_solution_rejects_player_id_with_invalid_characters(client):
    response = client.post(
        "/cases/case_museum_001/solution",
        json={"playerId": "not valid! id", "suspectId": "suspect_1"},
    )
    assert response.status_code == 422


def test_submit_solution_rejects_empty_suspect_id(client):
    player = client.post("/players").json()
    response = client.post(
        "/cases/case_museum_001/solution",
        json={"playerId": player["playerId"], "suspectId": ""},
    )
    assert response.status_code == 422


def test_submit_unknown_suspect_returns_400(client):
    player = client.post("/players").json()

    response = client.post(
        "/cases/case_museum_001/solution",
        json={"playerId": player["playerId"], "suspectId": "not-a-suspect"},
    )

    assert response.status_code == 400


def test_submit_unknown_case_returns_404(client):
    player = client.post("/players").json()

    response = client.post(
        "/cases/does-not-exist/solution",
        json={"playerId": player["playerId"], "suspectId": "suspect_1"},
    )

    assert response.status_code == 404


def test_submit_unknown_player_returns_404(client):
    response = client.post(
        "/cases/case_museum_001/solution",
        json={"playerId": "does-not-exist", "suspectId": "suspect_1"},
    )

    assert response.status_code == 404


def test_repeat_submission_scores_zero_and_flags_already_solved(client):
    """Closes the score/streak farming gap: resubmitting the same case must
    not keep granting score or advancing the streak — see task 3 of the
    security/ops audit."""
    player = client.post("/players").json()
    player_id = player["playerId"]

    first = client.post(
        "/cases/case_museum_001/solution",
        json={"playerId": player_id, "suspectId": "suspect_3"},
    ).json()
    assert first["score"] == 100
    assert first["streak"] == 1
    assert first["alreadySolved"] is False

    second = client.post(
        "/cases/case_museum_001/solution",
        json={"playerId": player_id, "suspectId": "suspect_3"},
    ).json()
    assert second["correct"] is True
    assert second["score"] == 0
    assert second["streak"] == 1
    assert second["alreadySolved"] is True

    score = client.get(f"/scores/{player_id}").json()
    assert score["totalScore"] == 100
    assert score["streak"] == 1


def test_submit_solution_rate_limits_by_caller(client):
    """Intended cluster-wide rate is 10/minute, but the enforced
    per-process value is ceil(10/3)=4 (app/api/rate_limiting.py's
    per_instance_limit) — see tasks 4 and 5 of the security/ops audit.
    Reuses one player across all calls deliberately (repeats after the
    first just come back already_solved, still a real 200) so this test
    isn't confounded by POST /players' own separate, independent limit."""
    player = client.post("/players").json()

    for _ in range(4):
        response = client.post(
            "/cases/case_museum_001/solution",
            json={"playerId": player["playerId"], "suspectId": "suspect_3"},
        )
        assert response.status_code == 200

    fifth = client.post(
        "/cases/case_museum_001/solution",
        json={"playerId": player["playerId"], "suspectId": "suspect_3"},
    )
    assert fifth.status_code == 429


def test_player_score_reflects_submission(client):
    player = client.post("/players").json()
    player_id = player["playerId"]

    client.post(
        "/cases/case_museum_001/solution",
        json={"playerId": player_id, "suspectId": "suspect_3"},
    )

    score = client.get(f"/scores/{player_id}").json()
    assert score["totalScore"] == 100
    assert score["streak"] == 1
