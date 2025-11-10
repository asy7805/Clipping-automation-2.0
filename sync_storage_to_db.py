#!/usr/bin/env python3
"""
Sync clips from Supabase storage to clips_metadata table
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set environment
os.environ['SUPABASE_URL'] = 'https://mpcvgknfjcxsalbtxabk.supabase.co'
os.environ['SUPABASE_ANON_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1wY3Zna25mamN4c2FsYnR4YWJrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMzMzY1MDcsImV4cCI6MjA2ODkxMjUwN30.34rKQx7iKYqtOqIUheiVT53gkVNxbGLjNyeoppQN2VY'

try:
    from db.supabase_client import get_client
    
    sb = get_client()
    print("=" * 60)
    print("SCANNING SUPABASE STORAGE FOR CLIPS")
    print("=" * 60)
    
    # List files in storage bucket
    bucket_name = "raw"
    print(f"\n📦 Checking bucket: {bucket_name}")
    
    try:
        # List all files in the raw bucket
        files = sb.storage.from_(bucket_name).list()
        print(f"✅ Found {len(files)} items in storage")
        
        for item in files[:20]:  # Show first 20
            name = item.get('name', 'unknown')
            size = item.get('metadata', {}).get('size', 0)
            created = item.get('created_at', 'unknown')
            print(f"   - {name} ({size} bytes) | {created}")
            
        if len(files) > 20:
            print(f"   ... and {len(files) - 20} more files")
            
    except Exception as e:
        print(f"❌ Error listing storage: {e}")
        print("\nℹ️ Storage listing requires service role key.")
        print("   Add SUPABASE_SERVICE_ROLE_KEY to .env and set USE_SERVICE_ROLE=true")
        sys.exit(1)
    
    # Check clips_metadata table
    print(f"\n📊 Checking clips_metadata table...")
    clips_in_db = sb.table("clips_metadata").select("id", count="exact").execute()
    print(f"   Records in database: {clips_in_db.count}")
    
    print("\n" + "=" * 60)
    print(f"Storage files: {len(files)}")
    print(f"Database records: {clips_in_db.count}")
    print(f"Missing: {len(files) - clips_in_db.count}")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

