#!/usr/bin/env python3
"""
Upload a captioned clip to Supabase storage.
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.supabase_client import get_client

def upload_captioned_clip(video_path: str, channel: str = "tenz"):
    """
    Upload a captioned video clip to Supabase storage.
    
    Args:
        video_path: Path to the captioned video file
        channel: Channel name (default: tenz)
    """
    os.environ["USE_SERVICE_ROLE"] = "true"
    sb = get_client()
    
    bucket = os.getenv("STORAGE_BUCKET", "raw")
    
    # Read video file
    video_file = Path(video_path)
    if not video_file.exists():
        print(f"❌ Video file not found: {video_path}")
        return None
    
    print(f"📹 Uploading: {video_file.name}")
    print(f"   Size: {video_file.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Create storage path
    timestamp = int(time.time())
    day = time.strftime("%Y%m%d")
    storage_path = f"captioned/{channel}/{day}/clip_{timestamp}.mp4"
    
    # Read video bytes
    with open(video_file, 'rb') as f:
        video_bytes = f.read()
    
    # Upload to Supabase
    try:
        file_options = {
            "content-type": "video/mp4",
            "upsert": "true"
        }
        
        result = sb.storage.from_(bucket).upload(storage_path, video_bytes, file_options)
        print(f"✅ Uploaded to: {bucket}/{storage_path}")
        
        # Get public URL
        from src.db.supabase_client import get_public_url
        public_url = get_public_url(bucket, storage_path)
        print(f"🔗 Public URL: {public_url}")
        
        return storage_path
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload captioned clip to Supabase")
    parser.add_argument("video", help="Path to captioned video file")
    parser.add_argument("--channel", default="tenz", help="Channel name")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("📤 Uploading Captioned Clip to Supabase")
    print("=" * 60)
    
    upload_captioned_clip(args.video, args.channel)

