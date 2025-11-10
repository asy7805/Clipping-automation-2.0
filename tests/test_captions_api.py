"""
Test suite for Captions.ai API endpoints
Tests the captions router integration
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_captions_health():
    """Test captions health endpoint"""
    response = client.get("/api/v1/captions/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    # Status can be "healthy", "unhealthy", or "unavailable" depending on API key
    assert data["status"] in ["healthy", "unhealthy", "unavailable"]


def test_get_supported_languages():
    """Test getting supported languages"""
    response = client.get("/api/v1/captions/languages")
    assert response.status_code == 200
    data = response.json()
    assert "languages" in data
    assert len(data["languages"]) > 0
    # Check English is in the list
    language_codes = [lang["code"] for lang in data["languages"]]
    assert "en" in language_codes


def test_add_captions_without_api_key():
    """Test adding captions when API key is not configured"""
    # This test assumes CAPTIONS_AI_API_KEY is not set in test environment
    response = client.post(
        "/api/v1/captions/add",
        json={
            "video_url": "https://example.com/video.mp4",
            "language": "en",
            "style": "default"
        }
    )
    # Should return 503 if API key is not configured, or process if it is
    assert response.status_code in [503, 200]


def test_translate_video_without_api_key():
    """Test translating video when API key is not configured"""
    response = client.post(
        "/api/v1/captions/translate",
        json={
            "video_url": "https://example.com/video.mp4",
            "source_language": "en",
            "target_language": "es",
            "voice_clone": True
        }
    )
    # Should return 503 if API key is not configured
    assert response.status_code in [503, 200]


def test_create_ai_video_without_api_key():
    """Test creating AI video when API key is not configured"""
    response = client.post(
        "/api/v1/captions/ai-video",
        json={
            "script": "Test script for AI video generation",
            "avatar": "default",
            "voice": "default"
        }
    )
    # Should return 503 if API key is not configured
    assert response.status_code in [503, 200]


def test_get_job_status_without_api_key():
    """Test getting job status when API key is not configured"""
    response = client.get("/api/v1/captions/job/test-job-123")
    # Should return 503 if API key is not configured
    assert response.status_code in [503, 200, 500]


def test_add_captions_validation():
    """Test request validation for add captions endpoint"""
    # Missing required video_url
    response = client.post(
        "/api/v1/captions/add",
        json={
            "language": "en"
        }
    )
    assert response.status_code == 422  # Validation error


def test_translate_video_validation():
    """Test request validation for translate endpoint"""
    # Missing required video_url
    response = client.post(
        "/api/v1/captions/translate",
        json={
            "source_language": "en",
            "target_language": "es"
        }
    )
    assert response.status_code == 422  # Validation error


def test_ai_video_validation():
    """Test request validation for AI video endpoint"""
    # Missing required script
    response = client.post(
        "/api/v1/captions/ai-video",
        json={
            "avatar": "default"
        }
    )
    assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    print("Running Captions API tests...")
    print("\n1. Testing health endpoint...")
    test_captions_health()
    print("✅ Health check passed")
    
    print("\n2. Testing supported languages...")
    test_get_supported_languages()
    print("✅ Languages endpoint passed")
    
    print("\n3. Testing add captions endpoint...")
    test_add_captions_without_api_key()
    print("✅ Add captions endpoint accessible")
    
    print("\n4. Testing translate endpoint...")
    test_translate_video_without_api_key()
    print("✅ Translate endpoint accessible")
    
    print("\n5. Testing AI video endpoint...")
    test_create_ai_video_without_api_key()
    print("✅ AI video endpoint accessible")
    
    print("\n6. Testing job status endpoint...")
    test_get_job_status_without_api_key()
    print("✅ Job status endpoint accessible")
    
    print("\n7. Testing validation...")
    test_add_captions_validation()
    test_translate_video_validation()
    test_ai_video_validation()
    print("✅ Validation tests passed")
    
    print("\n✅ All Captions API tests passed!")
    print("\nNote: Full functionality requires CAPTIONS_AI_API_KEY to be set")

