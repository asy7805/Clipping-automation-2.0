#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
os.environ["USE_SERVICE_ROLE"] = "true"

from src.db.supabase_client import get_client

sb = get_client()

print("🔍 Checking Supabase storage for midbeast clips...\n")

try:
    # List all folders in raw/midbeast
    folders = sb.storage.from_('raw').list('raw/midbeast')
    
    if not folders:
        print("❌ No folders found for midbeast")
        print("\nℹ️  This means clips are NOT being uploaded to Supabase yet.")
        print("   They might only be processing locally.")
    else:
        print(f"✅ Found {len(folders)} stream(s):\n")
        
        for folder in folders:
            folder_name = folder['name']
            print(f"📂 {folder_name}")
            
            # List files in this stream folder
            try:
                stream_folders = sb.storage.from_('raw').list(f'raw/midbeast/{folder_name}')
                for date_folder in stream_folders:
                    date_name = date_folder['name']
                    print(f"  📅 {date_name}")
                    
                    # List actual clips
                    clips = sb.storage.from_('raw').list(f'raw/midbeast/{folder_name}/{date_name}')
                    
                    print(f"  Total: {len(clips)} clips")
                    
                    for clip in clips[-5:]:  # Show last 5 clips
                        size_mb = clip.get('metadata', {}).get('size', 0) / (1024 * 1024)
                        name = clip.get('name', 'unknown')
                        print(f"    📹 {name} ({size_mb:.1f} MB)")
                    
            except Exception as e:
                print(f"  ⚠️  Error listing: {e}\n")
                
except Exception as e:
    print(f"❌ Error: {e}")



