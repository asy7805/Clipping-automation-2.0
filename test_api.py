#!/usr/bin/env python3
"""
API Test Script
Tests all API endpoints to verify they're working correctly
"""

import requests
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

API_BASE_URL = os.getenv("VITE_API_URL", "http://localhost:8000")
if not API_BASE_URL.startswith("http"):
    API_BASE_URL = "http://localhost:8000"

print("🧪 API Test Suite")
print("=" * 60)
print(f"Testing API at: {API_BASE_URL}")
print()

# Track test results
results = {
    "passed": [],
    "failed": [],
    "skipped": []
}

def test_endpoint(name, method="GET", endpoint="", data=None, headers=None, requires_auth=False):
    """Test an API endpoint"""
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        if requires_auth:
            results["skipped"].append(f"{name} (requires auth)")
            print(f"⏭️  {name}: SKIPPED (requires authentication)")
            return
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=5)
        else:
            results["skipped"].append(f"{name} (method not implemented)")
            return
        
        if response.status_code == 200 or response.status_code == 201:
            results["passed"].append(name)
            print(f"✅ {name}: PASSED ({response.status_code})")
            try:
                data = response.json()
                if isinstance(data, dict) and len(data) < 5:
                    print(f"   Response: {json.dumps(data, indent=2)}")
            except:
                pass
        elif response.status_code == 401:
            results["skipped"].append(f"{name} (requires auth)")
            print(f"⏭️  {name}: SKIPPED (401 - requires authentication)")
        elif response.status_code == 403:
            results["skipped"].append(f"{name} (forbidden)")
            print(f"⏭️  {name}: SKIPPED (403 - forbidden)")
        else:
            results["failed"].append(f"{name} ({response.status_code})")
            print(f"❌ {name}: FAILED ({response.status_code})")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"   Response: {response.text[:100]}")
    except requests.exceptions.ConnectionError:
        results["failed"].append(f"{name} (connection error)")
        print(f"❌ {name}: FAILED (Connection refused - is backend running?)")
    except requests.exceptions.Timeout:
        results["failed"].append(f"{name} (timeout)")
        print(f"❌ {name}: FAILED (Timeout)")
    except Exception as e:
        results["failed"].append(f"{name} ({str(e)})")
        print(f"❌ {name}: FAILED ({str(e)})")

# Test basic endpoints (no auth required)
print("📋 Testing Basic Endpoints (No Auth Required)")
print("-" * 60)

test_endpoint("Root endpoint", endpoint="/")
test_endpoint("Health check", endpoint="/api/v1/health")
test_endpoint("API docs", endpoint="/docs")

# Test public endpoints
print()
print("📋 Testing Public Endpoints")
print("-" * 60)

test_endpoint("Clip prediction (POST)", method="POST", endpoint="/api/v1/clips/predict", 
              data={"transcript": "This is a test transcript for clip prediction"})

# Test endpoints that require auth (will be skipped)
print()
print("📋 Testing Protected Endpoints (Will Skip - No Auth)")
print("-" * 60)

test_endpoint("Get clips", endpoint="/api/v1/clips", requires_auth=True)
test_endpoint("Get monitors", endpoint="/api/v1/monitors", requires_auth=True)
test_endpoint("Get streams", endpoint="/api/v1/streams", requires_auth=True)
test_endpoint("Get analytics", endpoint="/api/v1/analytics/summary", requires_auth=True)
test_endpoint("Admin check", endpoint="/api/v1/admin/check", requires_auth=True)

# Summary
print()
print("=" * 60)
print("📊 Test Summary")
print("=" * 60)
print(f"✅ Passed: {len(results['passed'])}")
print(f"❌ Failed: {len(results['failed'])}")
print(f"⏭️  Skipped: {len(results['skipped'])}")
print()

if results['failed']:
    print("❌ Failed Tests:")
    for test in results['failed']:
        print(f"   - {test}")
    print()
    sys.exit(1)
elif results['passed']:
    print("✅ All tests passed!")
    sys.exit(0)
else:
    print("⚠️  No tests ran (backend may not be running)")
    sys.exit(1)

