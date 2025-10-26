#!/usr/bin/env python3
"""Debug Supabase storage structure"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')
sb = create_client(url, key)
bucket = "raw"

print('🔍 STORAGE STRUCTURE DEBUG\n')

print('📂 Step 1: List root of bucket "raw"')
root_items = sb.storage.from_(bucket).list('', {'limit': 10})
print(f'   Found {len(root_items)} items:')
for item in root_items:
    print(f'   - {item["name"]}')

print('\n📂 Step 2: List inside "raw" folder')
raw_items = sb.storage.from_(bucket).list('raw', {'limit': 10})
print(f'   Found {len(raw_items)} items:')
for item in raw_items:
    print(f'   - {item["name"]} (type: {"file" if "." in item["name"] else "folder"})')

if raw_items:
    channel = raw_items[0]['name']
    print(f'\n📂 Step 3: List inside "raw/{channel}"')
    channel_files = sb.storage.from_(bucket).list(f'raw/{channel}', {'limit': 10})
    print(f'   Found {len(channel_files)} items:')
    for f in channel_files:
        name = f.get('name', 'N/A')
        print(f'   - {name}')
        if name.endswith('.mp4'):
            file_path = f'raw/{channel}/{name}'
            print(f'     ✅ MP4 file! Full path: {file_path}')
            url = sb.storage.from_(bucket).get_public_url(file_path)
            print(f'     🔗 Public URL: {url[:80]}...')


