#!/usr/bin/env python3
"""Fixed capture script - ensures no corruption"""
import argparse, os, sys, time, tempfile, subprocess, shutil
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.supabase_client import get_client, insert_row

SEGMENT_SECONDS = 30

def ensure_streams_row(sb, channel_name: str):
    payload = {
        "twitch_stream_id": f"live-{channel_name}-{int(time.time())}",
        "user_id": None,
        "channel_name": channel_name,
        "title": f"Live capture: {channel_name}",
        "category": None,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ended_at": None,
        "viewer_count": 0,
    }
    return insert_row("streams", payload)

def start_pipeline(channel: str, out_dir: Path):
    ffmpeg_path = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin\ffmpeg.exe")
    
    sl_cmd = ["streamlink", "--twitch-disable-ads", f"https://twitch.tv/{channel}", "best", "-O"]
    seg_pattern = str(out_dir / "seg_%05d.mp4")
    
    # CRITICAL FIX: Re-encode to ensure compatibility
    ff_cmd = [
        ffmpeg_path, "-hide_banner", "-loglevel", "warning",
        "-i", "pipe:0",
        # Video: Use libx264 with high quality
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",  # High quality (18 = near lossless)
        # Audio: Re-encode to AAC (ensures compatibility)
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",  # Standard sample rate
        # Output settings
        "-f", "segment",
        "-segment_time", str(SEGMENT_SECONDS),
        "-reset_timestamps", "1",
        "-movflags", "+faststart",  # Better streaming
        seg_pattern
    ]
    
    p_sl = subprocess.Popen(sl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p_ff = subprocess.Popen(ff_cmd, stdin=p_sl.stdout, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    p_sl.stdout.close()
    return p_sl, p_ff

def upload_segment(sb, bucket: str, local_path: Path, channel: str, stream_uid: str):
    day = time.strftime("%Y%m%d")
    key = f"raw/{channel}/{stream_uid}/{day}/{local_path.name}"
    
    # Wait for file to be fully written and stable
    for _ in range(5):
        size1 = local_path.stat().st_size
        time.sleep(1)
        size2 = local_path.stat().st_size
        if size1 == size2:
            break
    
    try:
        with open(local_path, 'rb') as f:
            file_data = f.read()
        
        # Verify file is valid
        if len(file_data) < 10000:  # At least 10KB
            print(f"WARNING: {local_path.name} too small ({len(file_data)} bytes)")
            return None
        
        # Verify it's a valid MP4
        if not file_data.startswith(b'\x00\x00\x00') and b'ftyp' not in file_data[:20]:
            print(f"WARNING: {local_path.name} doesn't appear to be valid MP4")
            return None
            
        sb.storage.from_(bucket).upload(key, file_data, {"upsert": "true"})
        return key
    except Exception as e:
        print(f"Upload error for {local_path.name}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True)
    args = parser.parse_args()

    if not shutil.which("streamlink"):
        print("ERROR: streamlink not found")
        sys.exit(1)

    os.environ["USE_SERVICE_ROLE"] = "true"
    sb = get_client()
    out_dir = Path(tempfile.mkdtemp(prefix=f"live_{args.channel}_"))
    print(f"Capturing {args.channel}")
    print(f"Output: {out_dir}")
    print("Using HIGH QUALITY encoding to prevent corruption")

    streams_row = ensure_streams_row(sb, args.channel)
    stream_uid = streams_row["twitch_stream_id"]
    print(f"Stream ID: {stream_uid}")
    print(f"Recording... (Ctrl+C to stop)\n")

    p_sl, p_ff = start_pipeline(args.channel, out_dir)
    
    known = set()
    uploaded = 0
    failed = 0
    
    try:
        while True:
            for file in sorted(out_dir.glob("seg_*.mp4")):
                if file not in known:
                    # Wait for file to be stable
                    size1 = file.stat().st_size if file.exists() else 0
                    time.sleep(3)
                    size2 = file.stat().st_size if file.exists() else 0
                    
                    if size1 == size2 and size2 > 0:
                        key = upload_segment(sb, "raw", file, args.channel, stream_uid)
                        known.add(file)
                        
                        if key:
                            uploaded += 1
                            mb = size2 / (1024 * 1024)
                            print(f"[{uploaded}] UPLOADED: {file.name} ({mb:.1f} MB) -> {key}")
                        else:
                            failed += 1
                            print(f"[FAILED] Skipped: {file.name}")
                        
                        # Clean up
                        try:
                            time.sleep(1)
                            file.unlink()
                        except Exception as e:
                            print(f"Cleanup warning: {e}")
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print(f"\n\nStopping capture...")
        print(f"Successfully uploaded: {uploaded} clips")
        print(f"Failed/Skipped: {failed} clips")
        p_sl.terminate()
        p_ff.terminate()
        p_sl.wait()
        p_ff.wait()
    finally:
        time.sleep(2)
        shutil.rmtree(out_dir, ignore_errors=True)
        print("Done.")

if __name__ == "__main__":
    main()
