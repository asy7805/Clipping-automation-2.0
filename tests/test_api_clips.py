import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Ensure src is on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "src"))

from api.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_list_clips(client):
    resp = client.get("/api/v1/clips?limit=1")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data
    assert "id" in data[0]


def test_get_clip(client):
    resp = client.get("/api/v1/clips/example-clip-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "example-clip-1"


@patch("api.routers.clips.is_clip_worthy_by_model", return_value=True)
def test_create_clip(mock_pred, client):
    payload = {"transcript": "Amazing moment!", "channel_name": "ch", "duration": 3.2}
    resp = client.post("/api/v1/clips", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["transcript"] == payload["transcript"]
    assert data["is_clip_worthy"] is True
    mock_pred.assert_called_once()


@patch("api.routers.clips.is_clip_worthy_by_model", return_value=False)
def test_predict_clip(mock_pred, client):
    payload = {"transcript": "meh", "model_version": "latest"}
    resp = client.post("/api/v1/clips/predict", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_clip_worthy"] is False
    assert data["model_version"] == "latest"
    mock_pred.assert_called_once()


