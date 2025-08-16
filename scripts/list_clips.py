#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.supabase_client import get_client, get_public_url

def list_streams():
    """List all streams in the database"""
    sb = get_client()
    response = sb.table("streams").select("*").execute()
    
    print("📺 Available Streams:")
    print("-" * 80)
    for stream in response.data:
        print(f"ID: {stream['id']}")
        print(f"Channel: {stream['channel_name']}")
        print(f"Title: {stream['title']}")
        print(f"Twitch ID: {stream['twitch_stream_id']}")
        print(f"Started: {stream['started_at']}")
        print("-" * 80)

def list_clips(stream_id=None, channel=None):
    """List clips for a specific stream or channel"""
    sb = get_client()
    bucket = os.getenv("STORAGE_BUCKET", "raw")
    
    if stream_id:
        # List clips for specific stream
        path = f"{channel}/{stream_id}/20250816/"  # Adjust date as needed
    elif channel:
        # List all clips for channel
        path = f"{channel}/"
    else:
        print("❌ Please specify --stream_id or --channel")
        return
    
    try:
        files = sb.storage.from_(bucket).list(path)
        print(f"📁 Clips in {path}:")
        print("-" * 80)
        
        for file in files:
            size_mb = file['metadata']['size'] / (1024 * 1024)
            print(f"📹 {file['name']} ({size_mb:.1f} MB)")
            
            # Get public URL if bucket is public
            try:
                url = get_public_url(bucket, f"{path}{file['name']}")
                print(f"   🔗 {url}")
            except:
                print(f"   🔒 Private file (use download method)")
            print()
            
    except Exception as e:
        print(f"❌ Error listing files: {e}")

def download_clip(path, output_file=None):
    """Download a specific clip"""
    sb = get_client()
    bucket = os.getenv("STORAGE_BUCKET", "raw")
    
    if not output_file:
        output_file = Path(path).name
    
    try:
        response = sb.storage.from_(bucket).download(path)
        with open(output_file, "wb") as f:
            f.write(response)
        print(f"✅ Downloaded: {path} -> {output_file}")
    except Exception as e:
        print(f"❌ Error downloading: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="List and access clips from Supabase Storage")
    parser.add_argument("--list-streams", action="store_true", help="List all streams")
    parser.add_argument("--list-clips", action="store_true", help="List clips")
    parser.add_argument("--channel", help="Channel name to list clips for")
    parser.add_argument("--stream-id", help="Specific stream ID to list clips for")
    parser.add_argument("--download", help="Download specific clip (path)")
    parser.add_argument("--output", help="Output filename for download")
    
    args = parser.parse_args()
    
    if args.list_streams:
        list_streams()
    elif args.list_clips:
        list_clips(args.stream_id, args.channel)
    elif args.download:
        download_clip(args.download, args.output)
    else:
        parser.print_help()
