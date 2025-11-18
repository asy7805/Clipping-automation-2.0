#!/usr/bin/env python3
"""
Check and fix file content types in Supabase storage
"""
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
os.environ["USE_SERVICE_ROLE"] = "true"

from src.db.supabase_client import get_client

sb = get_client()

print("🔍 Checking storage files...\n")

# List all files recursively
try:
    # List stream folders
    folders = sb.storage.from_('raw').list('raw/triplelift')
    
    for folder in folders:
        folder_name = folder['name']
        
        # List date folders
        date_folders = sb.storage.from_('raw').list(f'raw/triplelift/{folder_name}')
        
        for date_folder in date_folders:
            date_name = date_folder['name']
            path = f'raw/triplelift/{folder_name}/{date_name}'
            
            # List actual files
            files = sb.storage.from_('raw').list(path)
            
            print(f"📂 {path}")
            print(f"Found {len(files)} files:\n")
            
            for file in files[:5]:
                name = file.get('name', 'unknown')
                size = file.get('metadata', {}).get('size', 0)
                mime = file.get('metadata', {}).get('mimetype', 'unknown')
                
                print(f"  📄 {name}")
                print(f"     Size: {size:,} bytes ({size/1024/1024:.1f} MB)")
                print(f"     MIME: {mime}")
                
                # Try to download and check first few bytes
                try:
                    full_path = f'{path}/{name}'
                    data = sb.storage.from_('raw').download(full_path)
                    
                    # Check if it's really a video
                    if len(data) > 12:
                        magic = data[:12].hex()
                        print(f"     Header: {magic}")
                        
                        # MP4 files typically start with specific bytes
                        if b'ftyp' in data[:20]:
                            print(f"     ✅ Valid MP4 file")
                        else:
                            print(f"     ⚠️  Not a valid MP4 (starts with: {data[:20]})")
                    
                except Exception as e:
                    print(f"     ❌ Error downloading: {e}")
                
                print()
                
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()



