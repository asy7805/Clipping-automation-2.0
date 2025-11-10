"""
Simple test script to verify Captions.ai endpoints are accessible
Requires the API server to be running on port 8000
"""

import requests
import sys

BASE_URL = "http://localhost:8000/api/v1"


def test_health_endpoint():
    """Test the captions health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/captions/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to API server. Is it running on port 8000?")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_languages_endpoint():
    """Test the languages endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/captions/languages", timeout=5)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Languages found: {len(data.get('languages', []))}")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_add_captions_endpoint():
    """Test the add captions endpoint"""
    try:
        response = requests.post(
            f"{BASE_URL}/captions/add",
            json={
                "video_url": "https://example.com/test.mp4",
                "language": "en"
            },
            timeout=5
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        # 503 means not configured, 200 means configured
        return response.status_code in [200, 503]
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    print("=" * 60)
    print("Captions.ai API Endpoint Tests")
    print("=" * 60)
    print("\nNote: API server must be running on http://localhost:8000\n")
    
    tests = [
        ("Health Check", test_health_endpoint),
        ("Supported Languages", test_languages_endpoint),
        ("Add Captions", test_add_captions_endpoint),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\nTesting: {name}")
        print("-" * 60)
        passed = test_func()
        results.append((name, passed))
        print(f"Result: {'✅ PASSED' if passed else '❌ FAILED'}")
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

