#!/usr/bin/env python3
"""Manually upload 2 demo clips to Supabase"""
import os, sys, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.supabase_client import get_client, insert_row

# Get segments
seg_dir = Path("/var/folders/ds/267px0t926s0tg69t7sgz7x00000gn/T/test_jasontheween_sam_5tjt")
segments = sorted(seg_dir.glob("seg_*.mp4"))[:2]  # Get first 2

if len(segments) < 2:
    print(f"❌ Only found {len(segments)} segments")
    sys.exit(1)

print(f"📦 Found {len(segments)} segments to upload\n")

# Create stream record
os.environ["USE_SERVICE_ROLE"] = "true"
sb = get_client()
stream_row = insert_row("streams", {
    "twitch_stream_id": f"demo-jasontheween-{int(time.time())}",
    "channel_name": "jasontheween",
    "title": "Demo: 2 clips from jasontheween",
    "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "viewer_count": 0,
})
stream_uid = stream_row["twitch_stream_id"]
print(f"✅ Created stream record: {stream_uid}\n")

# Upload segments
uploaded = []
for i, seg in enumerate(segments, 1):
    print(f"📤 Uploading clip {i}/2: {seg.name}")
    
    with open(seg, "rb") as f:
        video_bytes = f.read()
    
    day = time.strftime("%Y%m%d")
    key = f"raw/jasontheween/{stream_uid}/{day}/clip_{i}_{int(time.time())}.mp4"
    
    file_options = {"content-type": "video/mp4", "upsert": "true"}
    sb.storage.from_("raw").upload(key, video_bytes, file_options)
    
    size_mb = len(video_bytes) / 1024 / 1024
    print(f"   ✅ Uploaded: {key} ({size_mb:.1f} MB)\n")
    uploaded.append(key)

print(f"🎉 SUCCESS! Uploaded 2 clips:")
for i, clip in enumerate(uploaded, 1):
    print(f"   {i}. {clip}")
    
print(f"\n🌐 View in Supabase:")
print(f"   https://app.supabase.com → Storage → raw bucket → raw/jasontheween/")

