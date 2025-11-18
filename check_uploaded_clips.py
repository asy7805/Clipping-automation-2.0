#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
os.environ["USE_SERVICE_ROLE"] = "true"

from src.db.supabase_client import get_client

sb = get_client()

print("🔍 Checking Supabase storage for triplelift clips...\n")

try:
    # List all folders in raw/triplelift
    folders = sb.storage.from_('raw').list('raw/triplelift')
    
    if not folders:
        print("❌ No folders found for triplelift")
    else:
        print(f"📁 Found {len(folders)} stream(s):\n")
        
        for folder in folders[:5]:  # Show first 5 streams
            folder_name = folder['name']
            print(f"📂 {folder_name}")
            
            # List files in this stream folder
            try:
                stream_folders = sb.storage.from_('raw').list(f'raw/triplelift/{folder_name}')
                for date_folder in stream_folders[:3]:  # Show first 3 dates
                    date_name = date_folder['name']
                    print(f"  📅 {date_name}")
                    
                    # List actual clips
                    clips = sb.storage.from_('raw').list(f'raw/triplelift/{folder_name}/{date_name}')
                    
                    for clip in clips[:10]:  # Show first 10 clips
                        size_mb = clip.get('metadata', {}).get('size', 0) / (1024 * 1024)
                        name = clip.get('name', 'unknown')
                        print(f"    📹 {name} ({size_mb:.1f} MB)")
                    
                    if len(clips) > 10:
                        print(f"    ... and {len(clips) - 10} more clips")
                    
                    print(f"  Total: {len(clips)} clips\n")
                    
            except Exception as e:
                print(f"  ⚠️  Error listing: {e}\n")
                
except Exception as e:
    print(f"❌ Error: {e}")




