#!/usr/bin/env python3
"""List clips in storage"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def list_clips():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    
    sb = create_client(url, key)
    
    print("=" * 60)
    print("📹 LISTING CLIPS IN STORAGE")
    print("=" * 60)
    
    folders = ['raw', 'raw/raw', 'captioned', 'smoke']
    
    for folder in folders:
        print(f"\n📁 {folder}:")
        try:
            files = sb.storage.from_('raw').list(folder, {'limit': 100})
            mp4_files = [f for f in files if f.get('name', '').endswith('.mp4')]
            other_folders = [f for f in files if '.' not in f.get('name', '')]
            
            print(f"  MP4 files: {len(mp4_files)}")
            print(f"  Subfolders: {len(other_folders)}")
            
            if mp4_files:
                print(f"  Sample clips:")
                for f in mp4_files[:5]:
                    name = f.get('name')
                    size = f.get('metadata', {}).get('size', 0) / (1024*1024)  # MB
                    print(f"    - {name} ({size:.1f} MB)")
            
            if other_folders:
                print(f"  Subfolders: {[f.get('name') for f in other_folders[:10]]}")
                
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    list_clips()

