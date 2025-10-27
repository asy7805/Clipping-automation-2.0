import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure src is on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from api.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_analytics_summary(client):
    resp = client.get("/api/v1/analytics/summary?days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_clips" in data
    assert "recent_activity" in data


def test_analytics_performance(client):
    resp = client.get("/api/v1/analytics/performance")
    assert resp.status_code == 200
    data = resp.json()
    assert "avg_confidence_score" in data
    assert "total_predictions" in data


def test_analytics_channels(client):
    resp = client.get("/api/v1/analytics/channels?limit=5&days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert "channel_name" in data[0]


def test_analytics_trends(client):
    resp = client.get("/api/v1/analytics/trends?days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert "trends" in data


