#!/usr/bin/env python3
"""
Direct test of posting functionality without Celery.
This will help us debug the posting process.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

from src.db.supabase_client import get_client
from src.posting.tasks import _download_video
from src.posting.youtube_publisher import YouTubePublisher

def test_posting():
    print("🧪 Testing posting functionality directly...")
    
    # Test 1: Check Supabase connection
    print("\n1. Testing Supabase connection...")
    try:
        supabase = get_client()
        print("✅ Supabase connection successful")
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return
    
    # Test 2: Check if we have a queue item
    print("\n2. Checking queue items...")
    try:
        result = supabase.table('posting_queue').select('*').eq('status', 'pending').limit(1).execute()
        if not result.data:
            print("❌ No pending queue items found")
            return
        
        queue_item = result.data[0]
        print(f"✅ Found queue item: {queue_item['id']}")
        print(f"   Clip ID: {queue_item['clip_id']}")
        print(f"   Status: {queue_item['status']}")
    except Exception as e:
        print(f"❌ Failed to get queue items: {e}")
        return
    
    # Test 3: Check social account
    print("\n3. Checking social account...")
    try:
        account_result = supabase.table('social_accounts').select('*').eq('id', queue_item['social_account_id']).execute()
        if not account_result.data:
            print("❌ Social account not found")
            return
        
        account = account_result.data[0]
        print(f"✅ Found social account: {account['account_name']} ({account['platform']})")
    except Exception as e:
        print(f"❌ Failed to get social account: {e}")
        return
    
    # Test 4: Test video download
    print("\n4. Testing video download...")
    try:
        video_path = _download_video(queue_item['clip_id'])
        print(f"✅ Video downloaded to: {video_path}")
        print(f"   File size: {os.path.getsize(video_path)} bytes")
    except Exception as e:
        print(f"❌ Video download failed: {e}")
        return
    
    # Test 5: Test YouTube publisher
    print("\n5. Testing YouTube publisher...")
    try:
        publisher = YouTubePublisher(
            access_token=account['access_token'],
            refresh_token=account.get('refresh_token')
        )
        print("✅ YouTube publisher created")
        
        # Test user info
        import asyncio
        user_info = asyncio.run(publisher.get_user_info())
        print(f"✅ User info: {user_info}")
        
    except Exception as e:
        print(f"❌ YouTube publisher failed: {e}")
        return
    
    print("\n🎉 All tests passed! The posting functionality should work.")
    print("The issue is likely with the Celery worker configuration.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_posting())
