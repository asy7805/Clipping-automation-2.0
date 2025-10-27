#!/usr/bin/env python3
"""
Complete workflow: Capture Twitch stream -> Add captions -> Upload to Supabase
"""

import os
import sys
import subprocess
import time
import signal
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.supabase_client import get_client


def capture_stream(channel: str, duration: int = 60) -> str:
    """Capture a Twitch stream for specified duration."""
    timestamp = int(time.time())
    output = f"{channel}_clip_{timestamp}.mp4"
    
    print(f"🎬 Capturing {duration}s from https://twitch.tv/{channel}...")
    
    try:
        cmd = ["streamlink", "https://www.twitch.tv/" + channel, "best", "--hls-live-restart", "-o", output]
        process = subprocess.Popen(cmd)
        
        # Wait for specified duration
        time.sleep(duration)
        
        # Stop the process
        process.terminate()
        process.wait(timeout=5)
        
        if Path(output).exists():
            print(f"✅ Captured: {output}")
            return output
        else:
            print(f"❌ Capture failed")
            return None
            
    except Exception as e:
        print(f"❌ Capture error: {e}")
        return None


def add_captions(video_path: str, style: str = "modern") -> str:
    """Add captions to video."""
    output = video_path.replace('.mp4', '_captioned.mp4')
    
    print(f"📝 Adding captions to {video_path}...")
    
    try:
        cmd = [
            sys.executable,
            "scripts/preedit_and_post.py",
            "--input", video_path,
            "--output", output,
            "--model", "tiny",
            "--style", style,
            "--keep-srt"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and Path(output).exists():
            print(f"✅ Captioned: {output}")
            return output
        else:
            print(f"❌ Captioning failed: {result.stderr[:500]}")
            return None
            
    except Exception as e:
        print(f"❌ Captioning error: {e}")
        return None


def upload_to_supabase(video_path: str, channel: str) -> str:
    """Upload video to Supabase storage."""
    os.environ["USE_SERVICE_ROLE"] = "true"
    sb = get_client()
    
    bucket = os.getenv("STORAGE_BUCKET", "raw")
    
    timestamp = int(time.time())
    day = time.strftime("%Y%m%d")
    storage_path = f"captioned/{channel}/{day}/clip_{timestamp}.mp4"
    
    print(f"📤 Uploading to Supabase...")
    
    try:
        with open(video_path, 'rb') as f:
            video_bytes = f.read()
        
        file_options = {"content-type": "video/mp4", "upsert": "true"}
        sb.storage.from_(bucket).upload(storage_path, video_bytes, file_options)
        
        print(f"✅ Uploaded to: {bucket}/{storage_path}")
        
        from src.db.supabase_client import get_public_url
        public_url = get_public_url(bucket, storage_path)
        print(f"🔗 Public URL: {public_url}")
        
        return storage_path
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Complete workflow: Capture -> Caption -> Upload")
    parser.add_argument("channel", nargs="?", default="tenz", help="Twitch channel name")
    parser.add_argument("--duration", type=int, default=60, help="Capture duration in seconds")
    parser.add_argument("--style", choices=['default', 'modern', 'bold', 'minimal'], default='modern', help="Caption style")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎬 Twitch Clip Automation")
    print("=" * 60)
    
    # Step 1: Capture
    print("\n[1/3] Capturing stream...")
    captured = capture_stream(args.channel, args.duration)
    if not captured:
        print("❌ Failed to capture")
        return
    
    # Step 2: Add captions
    print("\n[2/3] Adding captions...")
    captioned = add_captions(captured, args.style)
    if not captioned:
        print("❌ Failed to add captions")
        return
    
    # Step 3: Upload to Supabase
    print("\n[3/3] Uploading to Supabase...")
    uploaded = upload_to_supabase(captioned, args.channel)
    if not uploaded:
        print("❌ Failed to upload")
        return
    
    print("\n" + "=" * 60)
    print("✅ COMPLETE!")
    print("=" * 60)
    print(f"📹 Captured: {captured}")
    print(f"📝 Captioned: {captured.replace('.mp4', '_captioned.mp4')}")
    print(f"☁️  Uploaded: {uploaded}")


if __name__ == "__main__":
    main()

