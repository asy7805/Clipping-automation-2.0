#!/usr/bin/env python3
import argparse, os, sys, time, tempfile, subprocess, signal, shutil
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.supabase_client import get_client, insert_row, fetch_one

# Config
SEGMENT_SECONDS = 30

def ensure_streams_row(sb, channel_name: str, twitch_stream_id: Optional[str], user_id: Optional[str]):
    """
    Create a streams row if it doesn't exist yet (by twitch_stream_id if given, else by channel_name+created_at).
    Returns the row dict.
    """
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

def start_pipeline(channel: str, out_dir: Path):
    """
    Launches: streamlink -> stdout | ffmpeg -> 30s segments in out_dir/seg_00001.mp4
    Returns (proc_streamlink, proc_ffmpeg)
    """
    # streamlink: write video bytes to stdout (-O)
    sl_cmd = ["streamlink", "--twitch-disable-ads", f"https://twitch.tv/{channel}", "best", "-O"]
    # ffmpeg: read from stdin, write segmented mp4
    seg_pattern = str(out_dir / "seg_%05d.mp4")
    ff_cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-i", "pipe:0",
        "-c", "copy",
        "-f", "segment", "-segment_time", str(SEGMENT_SECONDS),
        "-reset_timestamps", "1",
        seg_pattern
    ]

    # Start streamlink and pipe to ffmpeg
    p_sl = subprocess.Popen(sl_cmd, stdout=subprocess.PIPE)
    p_ff = subprocess.Popen(ff_cmd, stdin=p_sl.stdout)
    # Ensure streamlink doesn't get SIGPIPE if ffmpeg exits
    p_sl.stdout.close()
    return p_sl, p_ff, seg_pattern

def upload_segment(sb, bucket: str, local_path: Path, storage_prefix: str, channel: str, stream_uid: str):
    # Compose storage key: raw/<channel>/<stream_uid>/YYYYMMDD/seg_xxxxx.mp4
    day = time.strftime("%Y%m%d")
    key = f"{storage_prefix}/{channel}/{stream_uid}/{day}/{local_path.name}"
    sb.storage.from_(bucket).upload(key, local_path.read_bytes(), {"upsert": "true"})
    return key

def main():
    parser = argparse.ArgumentParser(description="Live ingest Twitch channel in 30s segments and upload to Supabase.")
    parser.add_argument("--channel", required=True, help="Twitch channel name (e.g., xqc, pokimane)")
    parser.add_argument("--bucket", default=os.getenv("STORAGE_BUCKET", "raw"))
    parser.add_argument("--prefix", default="raw")
    parser.add_argument("--user_id", default=os.getenv("DEFAULT_USER_ID"))
    parser.add_argument("--stream_id", default=None, help="Optional known twitch_stream_id to attach to")
    args = parser.parse_args()

    # Set environment to use service role for database operations
    os.environ["USE_SERVICE_ROLE"] = "true"
    
    sb = get_client()
    out_dir = Path(tempfile.mkdtemp(prefix=f"live_{args.channel}_"))
    print(f"📁 Writing temp segments to: {out_dir}")

    # Create/ensure one streams row for this session
    streams_row = ensure_streams_row(sb, args.channel, args.stream_id, args.user_id)
    stream_uid = streams_row["twitch_stream_id"]
    print(f"🗂  Using streams row id={streams_row['id']} twitch_stream_id={stream_uid}")

    # Launch recorder pipeline
    p_sl, p_ff, seg_pattern = start_pipeline(args.channel, out_dir)
    print("▶️  Recording... (Ctrl+C to stop)")

    known = set()
    try:
        while True:
            # Poll for new files
            for file in sorted(out_dir.glob("seg_*.mp4")):
                if file not in known and file.stat().st_size > 0:
                    # Upload and log
                    key = upload_segment(sb, args.bucket, file, args.prefix, args.channel, stream_uid)
                    print(f"⬆️  Uploaded: {key} ({file.stat().st_size/1e6:.1f} MB)")
                    known.add(file)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹  Stopping...")
    finally:
        # Graceful shutdown
        for proc in (p_ff, p_sl):
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()

        # Optional: clean temp files
        # for f in out_dir.glob("seg_*.mp4"): f.unlink(missing_ok=True)
        # out_dir.rmdir()

    print("✅ Live ingest ended.")

if __name__ == "__main__":
    # Ensure ffmpeg/streamlink are available
    for bin_name in ("streamlink", "ffmpeg"):
        if not shutil.which(bin_name):
            print(f"❌ {bin_name} not found. Please install it first.")
            sys.exit(1)
    main()
