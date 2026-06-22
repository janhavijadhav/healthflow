from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'serving', 'fastapi'))

from unittest.mock import patch, MagicMock

def test_health_endpoint():
    with patch('main.get_bq_client'):
        from main import app
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "healthflow-api"
        assert "timestamp" in data

def test_health_returns_project():
    with patch('main.get_bq_client'):
        from main import app
        client = TestClient(app)
        response = client.get("/health")
        data = response.json()
        assert data["gcp_project"] == "healthflow-analytics-500100"
