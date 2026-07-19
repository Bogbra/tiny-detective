def test_openapi_schema_is_valid(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["openapi"].startswith("3.")

    expected_paths = {
        "/health",
        "/cases/daily",
        "/cases/{case_id}",
        "/cases/{case_id}/solution",
        "/cases/{case_id}/hint",
        "/players",
        "/players/{player_id}",
        "/scores/{player_id}",
        "/admin/cases/{case_id}/approve",
        "/admin/cases/{case_id}/reject",
        "/admin/cases/{case_id}/publish-daily",
        "/admin/cases/publish-next-daily",
    }
    assert expected_paths.issubset(schema["paths"].keys())
