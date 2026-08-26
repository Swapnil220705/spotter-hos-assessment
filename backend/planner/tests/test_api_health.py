import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_api_health_check_endpoint():
    """1. GET /api/health/ returns HTTP 200 with JSON status: ok without requiring payload or external services."""
    client = APIClient()
    response = client.get('/api/health/')

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "ok"
    assert res_data["service"] == "Spotter HOS Planner API"
    assert "version" in res_data
