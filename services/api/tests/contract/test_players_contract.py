def test_create_player_rate_limits_by_caller(client):
    """Intended cluster-wide rate is 10/minute, but the enforced
    per-process value is ceil(10/3)=4 (app/api/rate_limiting.py's
    per_instance_limit, default RATE_LIMIT_MAX_INSTANCES=3) — see tasks 4
    and 5 of the security/ops audit. Unauthenticated, no-AI-call endpoint,
    with no other backstop, which is why this one gets divided down."""
    for _ in range(4):
        response = client.post("/players")
        assert response.status_code == 201

    fifth = client.post("/players")
    assert fifth.status_code == 429
