#!/usr/bin/env python3
"""Upload 2 clips from stableronaldo"""
import os, sys, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.db.supabase_client import get_client, insert_row
from scripts.select_and_clip import detect_interest

# Get segments
seg_dir = Path("/var/folders/ds/267px0t926s0tg69t7sgz7x00000gn/T/test_stableronaldo_lktganyt")
segments = sorted(seg_dir.glob("seg_*.mp4"))[:4]  # Get first 4 to analyze

print(f"📦 Found {len(segments)} segments\n")

# Create stream record
os.environ["USE_SERVICE_ROLE"] = "true"
sb = get_client()
stream_row = insert_row("streams", {
    "twitch_stream_id": f"demo-stableronaldo-{int(time.time())}",
    "channel_name": "stableronaldo",
    "title": "Demo: Clips from stableronaldo @ TwitchCon",
    "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "viewer_count": 20241,
})
stream_uid = stream_row["twitch_stream_id"]
print(f"✅ Created stream record: {stream_uid}\n")

# Analyze and upload interesting ones
uploaded = []
for i, seg in enumerate(segments, 1):
    print(f"🔍 Analyzing clip {i}: {seg.name}")
    
    try:
        is_interesting = detect_interest(str(seg))
        
        if is_interesting:
            print(f"   ✅ INTERESTING! Uploading...")
            
            with open(seg, "rb") as f:
                video_bytes = f.read()
            
            day = time.strftime("%Y%m%d")
            key = f"raw/stableronaldo/{stream_uid}/{day}/clip_{len(uploaded)+1}_{int(time.time())}.mp4"
            
            file_options = {"content-type": "video/mp4", "upsert": "true"}
            sb.storage.from_("raw").upload(key, video_bytes, file_options)
            
            size_mb = len(video_bytes) / 1024 / 1024
            print(f"   📤 Uploaded: {size_mb:.1f} MB\n")
            uploaded.append(key)
            
            if len(uploaded) >= 2:
                print(f"✅ Got 2 interesting clips! Stopping...\n")
                break
        else:
            print(f"   ⏭️  Not interesting enough\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")

if len(uploaded) >= 2:
    print(f"🎉 SUCCESS! Uploaded 2 clips from stableronaldo:")
    for i, clip in enumerate(uploaded, 1):
        print(f"   {i}. {clip}")
    print(f"\n🌐 View in Supabase:")
    print(f"   Storage → raw bucket → raw/stableronaldo/")
else:
    print(f"⚠️  Only found {len(uploaded)} interesting clips")

