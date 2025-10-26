#!/usr/bin/env python3
"""
Quick test script to capture 2 interesting clips from a Twitch stream.
More conservative file handling to avoid incomplete MP4 issues.
"""
import argparse, os, sys, time, tempfile, subprocess, shutil
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.supabase_client import get_client, insert_row, fetch_one
from scripts.select_and_clip import detect_interest

SEGMENT_SECONDS = 30

def ensure_streams_row(sb, channel_name: str, user_id=None):
    """Create a streams record for this capture session."""
    payload = {
        "twitch_stream_id": f"test-{channel_name}-{int(time.time())}",
        "user_id": user_id,
        "channel_name": channel_name,
        "title": f"Test capture: {channel_name}",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "viewer_count": 0,
    }
    return insert_row("streams", payload)

def upload_segment(sb, bucket: str, video_bytes: bytes, storage_prefix: str, channel: str, stream_uid: str):
    """Upload video segment to Supabase storage."""
    day = time.strftime("%Y%m%d")
    key = f"{storage_prefix}/{channel}/{stream_uid}/{day}/clip_{int(time.time())}.mp4"
    
    file_options = {
        "content-type": "video/mp4",
        "upsert": "true"
    }
    
    try:
        result = sb.storage.from_(bucket).upload(key, video_bytes, file_options)
        return key
    except Exception as e:
        print(f"❌ Upload failed for {key}: {e}")
        raise

def start_pipeline(channel: str, out_dir: Path):
    """Start streamlink -> ffmpeg pipeline."""
    sl_cmd = ["streamlink", "--twitch-disable-ads", f"https://twitch.tv/{channel}", "best", "-O"]
    seg_pattern = str(out_dir / "seg_%05d.mp4")
    
    ff_cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-f", "segment",
        "-segment_time", str(SEGMENT_SECONDS),
        "-segment_format", "mp4",
        "-reset_timestamps", "1",
        "-movflags", "+faststart",
        "-avoid_negative_ts", "make_zero",
        "-g", "60",
        seg_pattern
    ]

    p_sl = subprocess.Popen(sl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p_ff = subprocess.Popen(ff_cmd, stdin=p_sl.stdout, stderr=subprocess.PIPE)
    p_sl.stdout.close()
    return p_sl, p_ff

def wait_for_stable_file(file_path: Path, stable_seconds: float = 3.0) -> bool:
    """Wait for file to be stable (not changing) for stable_seconds."""
    if not file_path.exists():
        return False
    
    last_size = -1
    stable_count = 0
    
    for _ in range(20):  # Try for up to 10 seconds
        try:
            current_size = file_path.stat().st_size
            if current_size == last_size and current_size > 1024:  # At least 1KB
                stable_count += 1
                if stable_count >= int(stable_seconds * 2):  # Check twice per second
                    return True
            else:
                stable_count = 0
            last_size = current_size
            time.sleep(0.5)
        except OSError:
            time.sleep(0.5)
    
    return False

def main():
    parser = argparse.ArgumentParser(description="Quick test: capture 2 interesting clips")
    parser.add_argument("--channel", required=True, help="Twitch channel name")
    parser.add_argument("--bucket", default=os.getenv("STORAGE_BUCKET", "raw"))
    parser.add_argument("--prefix", default="raw")
    parser.add_argument("--user_id", default=os.getenv("DEFAULT_USER_ID"))
    args = parser.parse_args()

    os.environ["USE_SERVICE_ROLE"] = "true"
    sb = get_client()
    out_dir = Path(tempfile.mkdtemp(prefix=f"test_{args.channel}_"))
    print(f"📁 Writing segments to: {out_dir}")

    streams_row = ensure_streams_row(sb, args.channel, args.user_id)
    stream_uid = streams_row["twitch_stream_id"]
    print(f"🗂 Stream ID: {stream_uid}")

    p_sl, p_ff = start_pipeline(args.channel, out_dir)
    print(f"▶️  Recording from {args.channel}... (will stop after 2 clips)")

    processed = set()
    interesting_clips = []
    
    try:
        while len(interesting_clips) < 2:
            # Find all segment files
            segments = sorted(out_dir.glob("seg_*.mp4"))
            
            for seg_file in segments:
                if seg_file in processed:
                    continue
                
                # Wait for file to be stable
                print(f"⏳ Waiting for {seg_file.name} to complete...")
                if not wait_for_stable_file(seg_file, stable_seconds=5.0):
                    print(f"⚠️  Skipping {seg_file.name} (unstable)")
                    processed.add(seg_file)
                    continue
                
                print(f"🔍 Analyzing {seg_file.name}...")
                
                try:
                    is_interesting = detect_interest(str(seg_file))
                    
                    if is_interesting:
                        print(f"✅ INTERESTING! Clip #{len(interesting_clips) + 1}")
                        
                        # Read and upload
                        with open(seg_file, "rb") as f:
                            video_bytes = f.read()
                        
                        key = upload_segment(sb, args.bucket, video_bytes, args.prefix, args.channel, stream_uid)
                        print(f"⬆️  Uploaded: {key}")
                        
                        interesting_clips.append(key)
                        
                        # Clean up
                        seg_file.unlink()
                    else:
                        print(f"⏭️  Not interesting, deleting...")
                        seg_file.unlink()
                    
                    processed.add(seg_file)
                    
                except Exception as e:
                    print(f"❌ Error processing {seg_file.name}: {e}")
                    processed.add(seg_file)
                    try:
                        seg_file.unlink()
                    except:
                        pass
            
            if len(interesting_clips) < 2:
                print(f"📊 Progress: {len(interesting_clips)}/2 clips found. Waiting for more segments...")
                time.sleep(3)
        
        print(f"\n🎉 SUCCESS! Captured 2 interesting clips:")
        for i, clip_key in enumerate(interesting_clips, 1):
            print(f"  {i}. {clip_key}")
            
    except KeyboardInterrupt:
        print("\n⏹ Stopped by user")
    finally:
        print("\n🧹 Cleaning up...")
        for proc in (p_ff, p_sl):
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except:
                    proc.kill()
        
        # Clean up remaining files
        for f in out_dir.glob("seg_*.mp4"):
            try:
                f.unlink()
            except:
                pass
        
        try:
            out_dir.rmdir()
        except:
            pass
        
        print("✅ Done!")

if __name__ == "__main__":
    for bin_name in ("streamlink", "ffmpeg"):
        if not shutil.which(bin_name):
            print(f"❌ {bin_name} not found. Please install it first.")
            sys.exit(1)
    main()

