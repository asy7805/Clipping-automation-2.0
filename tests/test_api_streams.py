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


def test_list_streams(client):
    resp = client.get("/api/v1/streams?limit=1")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data
    assert "id" in data[0]


def test_get_stream(client):
    resp = client.get("/api/v1/streams/stream-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "stream-1"


def test_create_stream(client):
    payload = {
        "twitch_stream_id": "twitch-1",
        "channel_name": "chan",
        "title": "title",
        "category": "Gaming",
        "viewer_count": 10,
    }
    resp = client.post("/api/v1/streams", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["twitch_stream_id"] == payload["twitch_stream_id"]


def test_live_streams(client):
    resp = client.get("/api/v1/streams/live")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_stream_clips(client):
    resp = client.get("/api/v1/streams/stream-1/clips?limit=1")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


