def test_create_player_rate_limits_by_caller(client):
    """10/minute (app/api/rate_limiting.py) — see task 4 of the security/ops
    audit. Unauthenticated, no-AI-call endpoint, but still a real write-
    volume vector without some bound."""
    for _ in range(10):
        response = client.post("/players")
        assert response.status_code == 201

    eleventh = client.post("/players")
    assert eleventh.status_code == 429
