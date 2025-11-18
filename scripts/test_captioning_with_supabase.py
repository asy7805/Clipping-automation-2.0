#!/usr/bin/env python3
"""
Test the captioning script with a raw video from Supabase Storage.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.supabase_client import get_client

def download_random_raw_video():
    """Download a random raw video from Supabase for testing."""
    # Try without service role first (use anon key)
    try:
        sb = get_client()
    except RuntimeError as e:
        # If that fails, check if service role is available
        if os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
            os.environ["USE_SERVICE_ROLE"] = "true"
            sb = get_client()
        else:
            print(f"❌ Cannot connect to Supabase: {e}")
            print("💡 You need SUPABASE_URL and either SUPABASE_ANON_KEY or SUPABASE_SERVICE_ROLE_KEY")
            return None
    bucket = os.getenv("STORAGE_BUCKET", "raw")
    
    print("🔍 Searching for raw videos in Supabase Storage...")
    
    try:
        # First, list all available buckets
        print("   Listing all buckets...")
        buckets = sb.storage.list_buckets()
        print(f"   Available buckets: {[b['id'] for b in buckets]}")
        
        # Try to list a specific directory path
        # Based on live_ingest.py, videos are stored in format: raw/{channel}/{stream_uid}/{date}/segment_X.mp4
        # Let's try listing the raw folder structure
        print("   Trying to list storage directories...")
        files = sb.storage.from_(bucket).list()
        
        if not files:
            print("   No files found in root. Trying specific paths...")
            
            # Try common channel names if you know them
            test_channels = ['xqc', 'pokimane', 'shroud', 'ninja']
            for channel in test_channels:
                try:
                    files = sb.storage.from_(bucket).list(f"{channel}/")
                    if files:
                        print(f"   ✅ Found files in {channel}/")
                        # Get first MP4
                        for f in files:
                            if f['name'].endswith('.mp4'):
                                video_path = f"{channel}/{f['name']}"
                                print(f"📹 Downloading: {video_path}")
                                data = sb.storage.from_(bucket).download(video_path)
                                
                                output_path = "test_raw_video.mp4"
                                with open(output_path, 'wb') as f:
                                    f.write(data)
                                print(f"✅ Downloaded to: {output_path}")
                                return output_path
                except:
                    continue
        
        # Filter for MP4 files
        mp4_files = [f for f in files if isinstance(f, dict) and f.get('name', '').endswith('.mp4')]
        
        if not mp4_files:
            print("❌ No MP4 files found in storage")
            print(f"   Bucket: {bucket}")
            print(f"   Files found: {len(files)}")
            return None
        
        print(f"✅ Found {len(mp4_files)} MP4 files")
        
        # Get the first available MP4
        video_file = mp4_files[0]
        print(f"📹 Downloading: {video_file['name']} ({(video_file['metadata']['size'] / 1024 / 1024):.1f} MB)")
        
        # Download the file
        output_path = f"test_raw_video.mp4"
        data = sb.storage.from_(bucket).download(video_file['name'])
        
        with open(output_path, 'wb') as f:
            f.write(data)
        
        print(f"✅ Downloaded to: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Error downloading video: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    video_path = download_random_raw_video()
    
    if video_path:
        print("\n" + "="*60)
        print("Now testing captioning with downloaded video...")
        print("="*60 + "\n")
        
        # Import and run the captioning script
        import subprocess
        result = subprocess.run([
            sys.executable, 
            "scripts/preedit_and_post.py",
            "--input", video_path,
            "--output", "test_captioned_supabase.mp4",
            "--model", "small",  # Use small model for faster testing
            "--keep-srt"
        ])
        
        if result.returncode == 0:
            print("\n✅ SUCCESS! Video has been captioned!")
            print(f"📹 Output: test_captioned_supabase.mp4")
            print(f"📝 Subtitle: test_captioned_supabase.srt")
        else:
            print("\n❌ Captioning failed")
    else:
        print("❌ Could not download video from Supabase")

