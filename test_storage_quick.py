#!/usr/bin/env python3
"""Quick test of Supabase storage structure"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_ANON_KEY')

sb = create_client(url, key)

print('📂 Listing root folders in raw bucket:')
channels = sb.storage.from_('raw').list('', {'limit': 100})
print(f'Found {len(channels)} items at root level')
for ch in channels:
    print(f"  - '{ch['name']}' (type: {ch.get('id', 'folder' if '.' not in ch['name'] else 'file')})")

if channels:
    print(f'\n📁 Listing files in first item: {channels[0]["name"]}')
    files = sb.storage.from_('raw').list(channels[0]['name'], {'limit': 10})
    print(f'Found {len(files)} items')
    for f in files:
        print(f"  - {f['name']} ({f.get('metadata', {}).get('size', 0)} bytes)")


