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
