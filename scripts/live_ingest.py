#!/usr/bin/env python3
import argparse, os, sys, time, tempfile, subprocess, shutil
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from select_and_clip import detect_interest  # Import the function from select_and_clip.py
from process import merge_segments, delete_from_supabase,select_best_segments
# Load environment variables from .env file
load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.supabase_client import get_client, insert_row, fetch_one

# Config
SEGMENT_SECONDS = 30

def ensure_streams_row(sb, channel_name: str, twitch_stream_id: Optional[str], user_id: Optional[str]):
    if twitch_stream_id:
        row = fetch_one("streams", twitch_stream_id=twitch_stream_id)
        if row:
            return row
    payload = {
        "twitch_stream_id": twitch_stream_id or f"live-{channel_name}-{int(time.time())}",
        "user_id": user_id,
        "channel_name": channel_name,
        "title": f"Live capture: {channel_name}",
        "category": None,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ended_at": None,
        "viewer_count": 0,
    }
    return insert_row("streams", payload)

def upload_segment(sb, bucket: str, video_bytes: bytes, storage_prefix: str, channel: str, stream_uid: str):
    day = time.strftime("%Y%m%d")
    key = f"{storage_prefix}/{channel}/{stream_uid}/{day}/segment_{int(time.time())}.mp4"
    
    # Fix: Use string values, not boolean
    file_options = {
        "content-type": "video/mp4",
        "upsert": "true"  # ← Must be string, not boolean
    }
    
    try:
        result = sb.storage.from_(bucket).upload(key, video_bytes, file_options)
        return key
    except Exception as e:
        print(f"❌ Upload failed for {key}: {e}")
        raise

def start_pipeline(channel: str, out_dir: Path):
    """Start streamlink -> ffmpeg pipeline with better segment handling."""
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
        "-segment_list_flags", "+live",
        "-segment_atclocktime", "1",
        "-reset_timestamps", "1",
        "-movflags", "+faststart+frag_keyframe+empty_moov",
        "-avoid_negative_ts", "make_zero",
        "-break_non_keyframes", "1",  # Ensure segments break cleanly
        "-g", "60",  # Keyframe interval
        seg_pattern
    ]

    p_sl = subprocess.Popen(sl_cmd, stdout=subprocess.PIPE)
    p_ff = subprocess.Popen(ff_cmd, stdin=p_sl.stdout)
    p_sl.stdout.close()
    return p_sl, p_ff, seg_pattern
def wait_for_file_complete(file_path: Path, stable_time: float = 8.0, check_interval: float = 0.5) -> bool:
    """Wait for file to be completely written by checking multiple indicators."""
    if not file_path.exists():
        return False
    
    last_size = -1
    last_mtime = -1
    stable_counter = 0
    
    while True:
        try:
            stat = file_path.stat()
            curr_size = stat.st_size
            curr_mtime = stat.st_mtime
            
            # File must be non-empty and both size and mtime must be stable
            if (curr_size == last_size and 
                curr_mtime == last_mtime and 
                curr_size > 0):
                stable_counter += check_interval
                if stable_counter >= stable_time:
                    # Additional check: try to open file exclusively
                    try:
                        # On Windows/some systems, this helps ensure file isn't being written
                        with open(file_path, "r+b") as f:
                            f.seek(0, 2)  # Seek to end
                            size_check = f.tell()
                            if size_check == curr_size:
                                return True
                    except (OSError, PermissionError):
                        # File might still be in use, wait more
                        stable_counter = 0
                        time.sleep(check_interval)
                        continue
            else:
                stable_counter = 0
                
            last_size = curr_size
            last_mtime = curr_mtime
            time.sleep(check_interval)
            
        except OSError:
            time.sleep(check_interval)
            continue
 

def safe_delete(file_path: Path, retries: int = 10, delay: float = 0.3) -> bool:
    for _ in range(retries):
        try:
            file_path.unlink()
            print(f"🗑️ Deleted {file_path.name}")
            return True
        except PermissionError:
            time.sleep(delay)
    print(f"⚠️ Could not delete {file_path.name}: still in use")
    return False

def delete_completed_batches(out_dir: Path, batch_size: int = 5):
    print("Delete command")
    files = sorted(f for f in out_dir.glob("seg_*.mp4") if wait_for_file_complete(f))
    while len(files) >= batch_size:
        print("Deletion init")
        batch = files[:batch_size]
        for f in batch:
            safe_delete(f)
        files = files[batch_size:]
def read_file_safely(file_path: Path, retries: int = 5, delay: float = 1.0) -> bytes:
    """Safely read file with retries and MP4 validation."""
    for attempt in range(retries):
        try:
            # Wait a bit more before reading
            time.sleep(0.5)
            
            with open(file_path, "rb") as f:
                data = f.read()
            
            # More thorough MP4 validation
            if len(data) < 32:
                raise ValueError("File too small to be valid MP4")
                
            # Check for MP4 signature
            if not (data.startswith(b'\x00\x00\x00') and b'ftyp' in data[:32]):
                raise ValueError("Invalid MP4 header signature")
            
            # Additional check: look for moov atom (indicates complete file)
            if b'moov' not in data:
                raise ValueError("MP4 missing moov atom - file incomplete")
                
            return data
            
        except (IOError, OSError, ValueError) as e:
            if attempt < retries - 1:
                print(f"⚠️ Attempt {attempt + 1} failed to read {file_path.name}: {e}")
                time.sleep(delay)
            else:
                print(f"❌ Failed to read {file_path.name} after {retries} attempts: {e}")
                raise

def main():
    parser = argparse.ArgumentParser(description="Live ingest Twitch channel in 30s segments and upload to Supabase.")
    parser.add_argument("--channel", required=True, help="Twitch channel name (e.g., xqc, pokimane)")
    parser.add_argument("--bucket", default=os.getenv("STORAGE_BUCKET", "raw"))
    parser.add_argument("--prefix", default="raw")
    parser.add_argument("--user_id", default=os.getenv("DEFAULT_USER_ID"))
    parser.add_argument("--stream_id", default=None, help="Optional known twitch_stream_id to attach to")
    args = parser.parse_args()

    os.environ["USE_SERVICE_ROLE"] = "true"
    sb = get_client()
    out_dir = Path(tempfile.mkdtemp(prefix=f"live_{args.channel}_"))
    print(f"📁 Writing temp segments to: {out_dir}")

    streams_row = ensure_streams_row(sb, args.channel, args.stream_id, args.user_id)
    stream_uid = streams_row["twitch_stream_id"]
    print(f"🗂 Using streams row id={streams_row['id']} twitch_stream_id={stream_uid}")

    p_sl, p_ff, seg_pattern = start_pipeline(args.channel, out_dir)
    print("▶️ Recording... (Ctrl+C to stop)")

    known = set()
    interesting_buffer=[]
    try:
        while True:
            print("Iteration happening")
            for file in sorted(out_dir.glob("seg_*.mp4")):
                if file not in known and wait_for_file_complete(file):
                    print(f"Processing {file.name}...")
                    if (detect_interest(file)):  # Call the function to process the segment
                        interesting_buffer.append(Path(file))
                        print(f"🔥 Added to buffer ({len(interesting_buffer)}/5): {file.name}")

                        # If 5 interesting clips collected
                        if len(interesting_buffer) >= 5:
                            try:
                                merged_path = out_dir / f"merged_{int(time.time())}.mp4"
                                top_segments = select_best_segments([str(p) for p in interesting_buffer], top_k=3)
                                top_segment_paths = [Path(s[0]) for s in top_segments]

                                merge_segments(top_segment_paths, merged_path)
                                video_bytes = read_file_safely(merged_path)
                                key = upload_segment(sb, args.bucket, video_bytes, args.prefix, args.channel, stream_uid)
                                print(f"⬆️ Uploaded merged clip: {key}")

                                # Delete original 5 segments from Supabase + local
                                for seg in interesting_buffer:
                                    delete_from_supabase(sb, args.bucket, seg.name, args.prefix, args.channel, stream_uid)
                                    safe_delete(seg)
                                    if seg in known:
                                        known.remove(seg)  # ✅ Remove from known
                                interesting_buffer.clear()
                                #safe_delete(merged_path)
                                continue

                            except Exception as e:
                                print(f"❌ Failed to merge batch: {e}")
                                # Don't clear buffer if error, try next iteration

                        known.add(file)

                    else:
                        print(f"⏭️ Skipped (not interesting): {file.name}")
                        known.add(file)
                        safe_delete(file)
            #delete_completed_batches(out_dir)
            time.sleep(2)  # Increased from 1 second

    except KeyboardInterrupt:
        print("\n⏹ Stopping...")

    finally:
        for proc in (p_ff, p_sl):
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()

        for f in out_dir.glob("seg_*.mp4"):
            safe_delete(f)
        try:
            out_dir.rmdir()
        except OSError:
            pass

    print("✅ Live ingest ended.")

if __name__ == "__main__":
    for bin_name in ("streamlink", "ffmpeg"):
        if not shutil.which(bin_name):
            print(f"❌ {bin_name} not found. Please install it first.")
            sys.exit(1)
    main()
