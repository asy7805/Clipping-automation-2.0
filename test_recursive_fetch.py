#!/usr/bin/env python3
"""Test the recursive fetch function"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
bucket = "raw"

def get_all_mp4_files(path="raw/raw", depth=0, max_depth=5):
    """Recursively find all MP4 files in storage"""
    if depth > max_depth:
        return []
    
    print(f"{'  ' * depth}📂 Scanning: {path}")
    all_files = []
    try:
        items = sb.storage.from_(bucket).list(path, {'limit': 1000})
        print(f"{'  ' * depth}   Found {len(items)} items")
        
        for item in items:
            item_name = item.get('name', '')
            full_path = f"{path}/{item_name}"
            
            # If it's an MP4 file, add it
            if item_name.endswith('.mp4'):
                print(f"{'  ' * depth}   ✅ MP4: {item_name}")
                all_files.append(full_path)
            # If it's a folder, recurse
            elif '.' not in item_name and item_name != '.emptyFolderPlaceholder':
                print(f"{'  ' * depth}   🔽 Folder: {item_name}")
                all_files.extend(get_all_mp4_files(full_path, depth + 1, max_depth))
                
    except Exception as e:
        print(f"{'  ' * depth}   ❌ Error: {e}")
        
    return all_files

print('🚀 Starting recursive search...\n')
mp4_files = get_all_mp4_files()
print(f'\n🎯 TOTAL MP4 FILES FOUND: {len(mp4_files)}')
print('\nFirst 5 files:')
for f in mp4_files[:5]:
    print(f'  - {f}')


