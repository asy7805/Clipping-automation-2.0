#!/usr/bin/env python3
import argparse, os, sys, time, tempfile, subprocess, shutil, json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import psutil  # For CPU monitoring
from select_and_clip import detect_interest  # Import the function from select_and_clip.py
from process import merge_segments, delete_from_supabase,select_best_segments
# Load environment variables from .env file
load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.supabase_client import get_client, insert_row, fetch_one, get_public_url
from src.api.services.credit_service import check_has_credits, deduct_credits, is_admin_user
from src.api.services.subscription_service import is_trial_user

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
        "started_at": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "ended_at": None,
        "viewer_count": 0,
    }
    try:
        return insert_row("streams", payload)
    except Exception as e:
        # If foreign key constraint fails (user_id doesn't exist), try with None
        if "foreign key constraint" in str(e).lower() or "23503" in str(e):
            print(f"⚠️ User {user_id} not found in users table, creating stream without user_id")
            payload["user_id"] = None
            return insert_row("streams", payload)
        raise

def get_ffmpeg_path():
    """Get FFmpeg path, checking multiple locations (Windows, macOS, Linux)."""
    # Check for Windows WinGet installation
    if os.name == 'nt':  # Windows
        winget_path = os.path.expandvars(
            r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin\ffmpeg.exe"
        )
        if os.path.exists(winget_path):
            return winget_path
    
    # Check common system paths
    for path in ["ffmpeg", "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg"]:
        if shutil.which(path):
            return path
    
    raise FileNotFoundError("FFmpeg not found. Please install FFmpeg.")

def compress_video(input_path: Path, output_path: Path, target_size_mb: float = 45.0, add_watermark: bool = False) -> bool:
    """Compress video to target size using FFmpeg. Optionally add watermark for trial users."""
    try:
        ffmpeg_path = get_ffmpeg_path()
        # Calculate target bitrate (rough estimate: bitrate = size * 8 / duration)
        # Assume 90 seconds average clip duration
        duration = 90
        target_bitrate_kbps = int((target_size_mb * 8 * 1024) / duration)
        
        cmd = [ffmpeg_path, "-y", "-i", str(input_path)]
        
        # Add watermark filter if requested
        if add_watermark:
            # Watermark text overlay using drawtext filter (works without fontfile on most systems)
            cmd.extend([
                "-vf", "drawtext=text='Created with ClipGen':fontcolor=white@0.7:fontsize=24:x=10:y=10"
            ])
        
        cmd.extend([
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-b:v", f"{target_bitrate_kbps}k", "-maxrate", f"{target_bitrate_kbps}k",
            "-bufsize", f"{target_bitrate_kbps * 2}k",
            "-c:a", "aac", "-b:a", "128k",
            str(output_path)
        ])
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and output_path.exists():
            original_size = input_path.stat().st_size / (1024 * 1024)
            compressed_size = output_path.stat().st_size / (1024 * 1024)
            watermark_text = " (with watermark)" if add_watermark else ""
            print(f"✅ Compressed to {compressed_size:.1f} MB (from {original_size:.1f} MB){watermark_text}")
            return True
        return False
    except Exception as e:
        print(f"❌ Compression failed: {e}")
        return False

def save_clip_to_database(sb, storage_key: str, bucket: str, channel: str, stream_uid: str, 
                          user_id: Optional[str], transcript: str, score: float, 
                          score_breakdown: dict, file_size: int, has_watermark: bool = False):
    """Save clip metadata to clips_metadata database table."""
    try:
        # Check credits before saving (if user_id provided)
        if user_id and not check_has_credits(user_id, 1):
            print(f"⚠️ User {user_id} has insufficient credits, skipping clip save")
            return None
        
        public_url = get_public_url(bucket, storage_key)
        breakdown_str = str(score_breakdown).replace("'", '"')
        formatted_transcript = f"Score: {score:.3f} | {breakdown_str}\n{transcript}"
        
        # Set expiration date for trial users (30 days) - admins have unlimited storage
        expires_at = None
        if user_id and is_trial_user(user_id) and not is_admin_user(user_id):
            from datetime import timedelta
            expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat().replace('+00:00', 'Z')
        
        clip_data = {
            'user_id': user_id,
            'channel_name': channel,
            'stream_id': stream_uid,
            'storage_path': storage_key,
            'storage_url': public_url,
            'file_size': file_size,
            'transcript': formatted_transcript,
            'confidence_score': float(score),
            'score_breakdown': score_breakdown,
            'has_watermark': has_watermark,
            'expires_at': expires_at,
            'created_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        }
        
        result = sb.table('clips_metadata').insert(clip_data).execute()
        if result.data:
            clip_id = result.data[0].get('id')
            print(f"✅ Inserted clip into database: {clip_id}")
            
            # Deduct credit after successful save
            if user_id:
                if deduct_credits(user_id, 1, 'clip_created', clip_id):
                    print(f"✅ Deducted 1 credit from user {user_id}")
                else:
                    print(f"⚠️ Failed to deduct credit for user {user_id} (clip still saved)")
            
            return clip_id
        return None
    except Exception as e:
        print(f"❌ Error saving clip to database: {e}")
        import traceback
        traceback.print_exc()
        return None

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
    sl_cmd = [
        "streamlink", 
        "--stream-segment-attempts", "3",
        "--stream-segment-threads", "1",
        "--stream-segment-timeout", "10",
        "--stream-timeout", "30",
        f"https://twitch.tv/{channel}", 
        "best", 
        "-O"
    ]
    seg_pattern = str(out_dir / "seg_%05d.mp4")
    
    ffmpeg_path = get_ffmpeg_path()
    
    # Create log directories
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    sl_log = log_dir / f"streamlink_{channel}.log"
    ff_log = log_dir / f"ffmpeg_{channel}.log"
    
    sl_log_handle = open(sl_log, 'a')
    ff_log_handle = open(ff_log, 'a')
    
    print(f"📝 Streamlink log: {sl_log}")
    print(f"📝 FFmpeg log: {ff_log}")
    
    ff_cmd = [
        ffmpeg_path, "-hide_banner", "-loglevel", "warning",
        "-fflags", "+discardcorrupt+ignidx",
        "-err_detect", "ignore_err",
        "-i", "pipe:0",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",  # Lower CPU: ultrafast preset, higher CRF
        "-c:a", "aac", "-b:a", "128k",
        "-f", "segment",
        "-segment_time", str(SEGMENT_SECONDS),
        "-segment_format", "mp4",
        "-segment_list_flags", "+live",
        "-segment_atclocktime", "1",
        "-reset_timestamps", "1",
        "-movflags", "+frag_keyframe",  # Fragmented MP4s readable while writing - moov atom written immediately
        "-avoid_negative_ts", "make_zero",
        "-break_non_keyframes", "1",
        "-g", "60",
        "-force_key_frames", f"expr:gte(t,n_forced*{SEGMENT_SECONDS})",
        "-segment_time_metadata", "1",
        "-write_tmcd", "0",
        "-max_muxing_queue_size", "1024",
        "-analyzeduration", "2000000",
        "-probesize", "2000000",
        seg_pattern
    ]

    p_sl = subprocess.Popen(sl_cmd, stdout=subprocess.PIPE, stderr=sl_log_handle, bufsize=1)
    
    time.sleep(0.5)
    if p_sl.poll() is not None:
        sl_log_handle.close()
        ff_log_handle.close()
        exit_code = p_sl.returncode
        raise RuntimeError(f"Streamlink died immediately with exit code {exit_code}")
    
    p_ff = subprocess.Popen(ff_cmd, stdin=p_sl.stdout, stderr=ff_log_handle, bufsize=1)
    p_sl.stdout.close()
    
    print(f"✅ Pipeline started: streamlink PID {p_sl.pid}, ffmpeg PID {p_ff.pid}")
    
    return p_sl, p_ff, seg_pattern
def wait_for_file_complete(file_path: Path, stable_time: float = 5.0, check_interval: float = 0.2, max_wait: float = 15.0) -> bool:
    """Wait for file to be completely written with timeout."""
    if not file_path.exists():
        return False
    
    start_time = time.time()
    last_size = -1
    last_mtime = -1
    stable_counter = 0
    
    # Disabled quick check to prevent race conditions
    if False:  # validate_mp4_file(file_path):
        time.sleep(0.1)
        stat2 = file_path.stat()
        if stat2.st_size > 0:
            return True
    
    while (time.time() - start_time) < max_wait:
        try:
            stat = file_path.stat()
            curr_size = stat.st_size
            curr_mtime = stat.st_mtime
            
            if (curr_size == last_size and curr_mtime == last_mtime and curr_size > 0):
                stable_counter += check_interval
                if stable_counter >= stable_time:
                    try:
                        with open(file_path, "r+b") as f:
                            f.seek(0, 2)
                            size_check = f.tell()
                            if size_check == curr_size:
                                if validate_mp4_file(file_path):
                                    return True
                                # If validation fails, continue waiting (file might still be writing)
                                stable_counter = max(0, stable_counter - check_interval)
                    except (OSError, PermissionError):
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
    
    return False

def validate_mp4_file(file_path: Path) -> bool:
    """Validate that the MP4 file is properly formatted and has moov atom."""
    try:
        file_size = file_path.stat().st_size
        if file_size < 10000:
            return False
        
        with open(file_path, "rb") as f:
            header = f.read(32)
            if len(header) < 32:
                return False
            
            if not (header.startswith(b'\x00\x00\x00') and b'ftyp' in header[:32]):
                return False
            
            # Check for moov atom - check both beginning and end efficiently
            f.seek(0)
            first_128kb = f.read(min(131072, file_size))
            if b'moov' in first_128kb:
                return True
            
            if file_size > 131072:
                f.seek(max(0, file_size - 131072), 0)
                last_128kb = f.read(131072)
                if b'moov' in last_128kb:
                    return True
            else:
                if b'moov' in first_128kb:
                    return True
            
            return False
    except Exception as e:
        return False
 

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

    def update_buffer_state():
        """Update buffer state file for monitoring."""
        try:
            buffer_state_file = Path(tempfile.gettempdir()) / f"buffer_state_{args.channel}_{stream_uid[:8]}.json"
            buffer_state = {
                'buffer_count': len(interesting_buffer),
                'buffer_total': 5,
                'buffer_progress': len(interesting_buffer) / 5.0,
                'buffer_status': 'filling' if len(interesting_buffer) < 5 else 'ready',
                'last_update': time.time()
            }
            with open(buffer_state_file, 'w') as f:
                json.dump(buffer_state, f)
        except Exception:
            pass  # Non-critical
    
    known = set()
    interesting_buffer = []
    iteration_count = 0
    
    try:
        while True:
            # Check session limit for trial users (1 hour) - admins have unlimited sessions
            if args.user_id and is_trial_user(args.user_id) and not is_admin_user(args.user_id):
                monitor_info = sb.table('monitors').select('session_started_at').eq('user_id', args.user_id).eq('channel_name', args.channel).execute()
                if monitor_info.data and monitor_info.data[0].get('session_started_at'):
                    session_start_str = monitor_info.data[0]['session_started_at']
                    try:
                        session_start = datetime.fromisoformat(session_start_str.replace('Z', '+00:00'))
                        elapsed = (datetime.now(timezone.utc) - session_start).total_seconds()
                        if elapsed > 3600:  # 1 hour = 3600 seconds
                            print("⏰ Trial session limit reached (1 hour). Stopping monitor.")
                            print("💡 Upgrade to Pro for unlimited sessions.")
                            # Update monitor status to stopped
                            sb.table('monitors').update({
                                'status': 'stopped',
                                'stopped_at': datetime.now(timezone.utc).isoformat()
                            }).eq('user_id', args.user_id).eq('channel_name', args.channel).execute()
                            break
                        elif elapsed > 3000:  # Warn at 50 minutes
                            remaining_minutes = int((3600 - elapsed) / 60)
                            print(f"⚠️ Trial session: {remaining_minutes} minutes remaining")
                    except Exception as e:
                        print(f"⚠️ Error checking session limit: {e}")
            
            iteration_count += 1
            
            # Check process health and restart if needed
            if p_sl.poll() is not None or p_ff.poll() is not None:
                print(f"⚠️ Pipeline process died! Streamlink: {p_sl.poll()}, FFmpeg: {p_ff.poll()}")
                print("🔄 Restarting pipeline...")
                interesting_buffer.clear()
                known.clear()
                update_buffer_state()
                p_sl, p_ff, seg_pattern = start_pipeline(args.channel, out_dir)
                print("✅ Pipeline restarted")
                time.sleep(5)
                continue
            
            if iteration_count % 20 == 0:
                print(f"🔄 Iteration {iteration_count}: {len(known)} segments processed, {len(interesting_buffer)} in buffer")
                update_buffer_state()
            
            # Get all segment files and sort them
            # We use file modification time, but file name number is safer for ordering
            all_segments = sorted(out_dir.glob("seg_*.mp4"), key=lambda p: p.name)
            
            # Ignore the latest segment as it might still be writing
            if len(all_segments) > 0:
                segments_to_process = all_segments[:-1]
            else:
                segments_to_process = []
            
            segments_processed_this_iteration = 0
            max_segments_per_iteration = 5
            
            for file in segments_to_process:
                if segments_processed_this_iteration >= max_segments_per_iteration:
                    break
                if file in known:
                    continue
                
                # No need to check file age anymore, because we only process if a newer segment exists
                # But we still run validation just in case
                
                # Wait for file to be complete AND validate it can be opened by FFmpeg
                if wait_for_file_complete(file, stable_time=2.0, max_wait=10.0):
                    # Double-check file is still valid before processing (race condition protection)
                    if not validate_mp4_file(file):
                        print(f"⚠️ File {file.name} failed validation after wait, skipping")
                        continue
                    
                    print(f"📹 Processing {file.name}...")
                    segments_processed_this_iteration += 1
                    try:
                        if detect_interest(file):
                            interesting_buffer.append(Path(file))
                            print(f"🔥 Added to buffer ({len(interesting_buffer)}/5): {file.name}")
                            update_buffer_state()
                            
                            if len(interesting_buffer) >= 5:
                                try:
                                    merged_path = out_dir / f"merged_{int(time.time())}.mp4"
                                    top_segments = select_best_segments([str(p) for p in interesting_buffer], top_k=3)
                                    top_segment_paths = [Path(s[0]) for s in top_segments]
                                    
                                    merge_segments(top_segment_paths, merged_path)
                                    
                                    # Check if watermarking is needed (trial users only) - admins never get watermarks
                                    should_watermark = args.user_id and is_trial_user(args.user_id) and not is_admin_user(args.user_id)
                                    
                                    # Check file size and compress if needed
                                    file_size_mb = merged_path.stat().st_size / (1024 * 1024)
                                    if file_size_mb > 45:
                                        print(f"⚠️ Merged clip too large ({file_size_mb:.1f} MB), compressing...")
                                        compressed_path = out_dir / f"compressed_{int(time.time())}.mp4"
                                        if compress_video(merged_path, compressed_path, add_watermark=should_watermark):
                                            merged_path = compressed_path
                                            file_size_mb = compressed_path.stat().st_size / (1024 * 1024)
                                    elif should_watermark:
                                        # Even if file is small, add watermark for trial users
                                        print(f"💧 Adding watermark for trial user...")
                                        compressed_path = out_dir / f"watermarked_{int(time.time())}.mp4"
                                        if compress_video(merged_path, compressed_path, add_watermark=True):
                                            merged_path = compressed_path
                                    
                                    video_bytes = read_file_safely(merged_path)
                                    storage_key = upload_segment(sb, args.bucket, video_bytes, args.prefix, args.channel, stream_uid)
                                    print(f"⬆️ Uploaded merged clip: {storage_key}")
                                    
                                    # Get transcript and score from best segments
                                    transcript = top_segments[0][2] if top_segments else ""
                                    score = top_segments[0][1] if top_segments else 0.0
                                    score_breakdown = top_segments[0][3] if top_segments and len(top_segments[0]) > 3 else {}
                                    
                                    # Save to database
                                    save_clip_to_database(
                                        sb, storage_key, args.bucket, args.channel, stream_uid,
                                        args.user_id, transcript, score, score_breakdown, len(video_bytes),
                                        has_watermark=should_watermark
                                    )
                                    
                                    # Delete original segments
                                    for seg in interesting_buffer:
                                        delete_from_supabase(sb, args.bucket, seg.name, args.prefix, args.channel, stream_uid)
                                        safe_delete(seg)
                                        if seg in known:
                                            known.remove(seg)
                                    interesting_buffer.clear()
                                    update_buffer_state()
                                    
                                except Exception as e:
                                    print(f"❌ Failed to merge batch: {e}")
                                    import traceback
                                    traceback.print_exc()
                                    # Clear buffer on error to prevent infinite loop
                                    if "Payload too large" in str(e) or "413" in str(e):
                                        interesting_buffer.clear()
                                        update_buffer_state()
                            
                            known.add(file)
                        else:
                            print(f"⏭️ Skipped (not interesting): {file.name}")
                            known.add(file)
                            safe_delete(file)
                            
                    except Exception as e:
                        print(f"❌ Error processing {file.name}: {e}")
                        import traceback
                        traceback.print_exc()
                        print(f"🗑️ Deleting corrupted file: {file.name}")
                        known.add(file)
                        safe_delete(file)
                    
                    # Small sleep after processing each segment to reduce CPU load
                    # This prevents CPU spikes while still allowing timely processing
                    time.sleep(0.5)
            
            # Main loop sleep - increased slightly to reduce CPU usage
            time.sleep(3)

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
    # Check streamlink
    if not shutil.which("streamlink"):
        print("❌ streamlink not found. Please install it first.")
        sys.exit(1)
    
    # Check ffmpeg
    try:
        get_ffmpeg_path()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    main()
