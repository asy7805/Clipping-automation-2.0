#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["USE_SERVICE_ROLE"] = "true"

from src.db.supabase_client import get_client

sb = get_client()

session_id = "live-midbeast-1760939172"

print(f"🔍 Checking for current session: {session_id}\n")

try:
    # Check if this session folder exists
    result = sb.storage.from_('raw').list(f'raw/midbeast/{session_id}')
    
    if result:
        print(f"✅ Session folder exists!")
        for date_folder in result:
            date_name = date_folder['name']
            print(f"  📅 {date_name}")
            
            clips = sb.storage.from_('raw').list(f'raw/midbeast/{session_id}/{date_name}')
            print(f"  Found {len(clips)} clips:")
            
            for clip in clips:
                size_mb = clip.get('metadata', {}).get('size', 0) / (1024 * 1024)
                name = clip.get('name', 'unknown')
                print(f"    📹 {name} ({size_mb:.1f} MB)")
    else:
        print(f"❌ Session folder does NOT exist yet")
        print(f"\n⚠️  This means clips are being processed but NOT uploaded to Supabase")
        print(f"   The script might be waiting for the buffer to fill or merge segments")
        
except Exception as e:
    print(f"❌ Session folder does NOT exist: {e}")
    print(f"\n⚠️  Clips are NOT being uploaded to Supabase raw storage")



