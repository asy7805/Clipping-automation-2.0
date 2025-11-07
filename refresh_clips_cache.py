#!/usr/bin/env python3
"""Manually refresh the clips cache"""
import requests
import time

API_BASE = "http://localhost:8000/api/v1"

print("🔄 Refreshing clips cache...")
print("This may take 30-60 seconds...")

start = time.time()

try:
    # The clips endpoint should cache on first call
    response = requests.get(f"{API_BASE}/clips?limit=100", timeout=120)
    
    elapsed = time.time() - start
    
    if response.status_code == 200:
        data = response.json()
        clips = data.get('clips', [])
        print(f"✅ SUCCESS! ({elapsed:.1f}s)")
        print(f"📹 Loaded {len(clips)} clips into cache")
        print(f"📊 Total clips: {data.get('pagination', {}).get('total', 0)}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        
except requests.exceptions.Timeout:
    print("❌ Timeout after 120 seconds")
except Exception as e:
    print(f"❌ Error: {e}")

