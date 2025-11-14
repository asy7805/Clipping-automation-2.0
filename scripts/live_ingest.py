#!/usr/bin/env python3
import argparse, os, sys, time, tempfile, subprocess, shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone
from dotenv import load_dotenv

# Fix tokenizer parallelism warning BEFORE importing models
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from select_and_clip import detect_interest  # Import the function from select_and_clip.py
from process import merge_segments, delete_from_supabase,select_best_segments

# Force unbuffered output for real-time logging
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Load environment variables from .env file
load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.supabase_client import get_client, insert_row, fetch_one

# Config
SEGMENT_SECONDS = 30
DEFAULT_STREAM_QUALITY = os.getenv("STREAM_QUALITY", "best")
DEFAULT_ENCODER = os.getenv("FFMPEG_ENCODER", "auto")  # auto|cpu|videotoolbox|cuda|qsv|copy
DEFAULT_VIDEO_BITRATE = int(os.getenv("FFMPEG_VIDEO_BITRATE", "3000"))  # kbps
DEFAULT_AUDIO_BITRATE = int(os.getenv("FFMPEG_AUDIO_BITRATE", "128"))   # kbps
DEFAULT_SCALE_WIDTH = int(os.getenv("FFMPEG_SCALE_WIDTH", "1280"))      # px, 0 = keep source

def resolve_encoder(preference: str) -> str:
    """Resolve encoder shortcut into a concrete implementation."""
    preference = (preference or "cpu").lower()
    if preference == "auto":
        if sys.platform == "darwin":
            return "videotoolbox"
        elif sys.platform == "win32":
            # Windows: Check for NVIDIA GPU, Intel QuickSync, or use CPU
            if shutil.which("nvidia-smi"):
                return "cuda"
            # Check for Intel QuickSync on Windows (DXVA2)
            try:
                # Try to detect Intel GPU via dxva2
                return "dxva2"  # Windows hardware acceleration
            except:
                return "cpu"
        # Linux
        if shutil.which("nvidia-smi"):
            return "cuda"
        # Simple heuristic for Intel QuickSync
        if sys.platform.startswith("linux") and Path("/dev/dri").exists():
            return "qsv"
        return "cpu"
    return preference

def build_ffmpeg_command(seg_pattern: str, encoder: str, video_bitrate: int, audio_bitrate: int, scale_width: int) -> List[str]:
    """Build an FFmpeg command tailored to the chosen encoder."""
    common_segment_flags = [
        "-f", "segment",
        "-segment_time", str(SEGMENT_SECONDS),
        "-segment_format", "mp4",
        "-segment_list_flags", "+live",
        "-segment_atclocktime", "1",
        "-segment_time_metadata", "1",
        "-reset_timestamps", "1",
        "-movflags", "+faststart+frag_keyframe+empty_moov",
        "-avoid_negative_ts", "make_zero",
        "-break_non_keyframes", "1",
        "-max_muxing_queue_size", "1024",
        "-analyzeduration", "2000000",
        "-probesize", "2000000",
    ]

    if encoder == "copy":
        return [
            "ffmpeg", "-hide_banner", "-loglevel", "warning",
            "-i", "pipe:0",
            "-c", "copy",
            "-map", "0",
            *common_segment_flags,
            seg_pattern
        ]

    vf_filter = []
    if scale_width and scale_width > 0:
        vf_filter = ["-vf", f"scale={scale_width}:-2"]

    # Hardware acceleration flags must come BEFORE -i input
    hwaccel_flags = []
    codec_flags = []
    
    if encoder == "videotoolbox":
        hwaccel_flags = ["-hwaccel", "videotoolbox"]
        codec_flags = [
            "-c:v", "h264_videotoolbox",
            "-b:v", f"{video_bitrate}k",
            "-maxrate", f"{int(video_bitrate * 1.2)}k",
            "-bufsize", f"{video_bitrate * 2}k",
        ]
    elif encoder == "cuda":
        hwaccel_flags = ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
        codec_flags = [
            "-c:v", "h264_nvenc",
            "-preset", "p4",
            "-b:v", f"{video_bitrate}k",
            "-maxrate", f"{int(video_bitrate * 1.2)}k",
            "-bufsize", f"{video_bitrate * 2}k",
        ]
    elif encoder == "qsv":
        hwaccel_flags = ["-hwaccel", "qsv"]
        codec_flags = [
            "-c:v", "h264_qsv",
            "-global_quality", "22",
            "-b:v", f"{video_bitrate}k",
        ]
    elif encoder == "dxva2":
        # Windows hardware acceleration (DXVA2)
        hwaccel_flags = ["-hwaccel", "dxva2"]
        codec_flags = [
            "-c:v", "h264_nvenc" if shutil.which("nvidia-smi") else "libx264",
            "-preset", "fast",
            "-b:v", f"{video_bitrate}k",
        ]
    else:
        # CPU encoding (no hardware acceleration)
        codec_flags = [
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
        ]

    return [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        *hwaccel_flags,  # Hardware acceleration BEFORE input
        "-i", "pipe:0",
        "-fflags", "+discardcorrupt+ignidx",
        "-err_detect", "ignore_err",
        *vf_filter,
        *codec_flags,  # Codec settings AFTER input
        "-force_key_frames", "expr:gte(t,n_forced*30)",
        "-g", "60",
        "-threads", "2",
        "-c:a", "aac",
        "-b:a", f"{audio_bitrate}k",
        *common_segment_flags,
        seg_pattern
    ]

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
    return insert_row("streams", payload)

def compress_video(input_path: Path, output_path: Path, target_size_mb: float = 40):
    """Compress video to target size using FFmpeg."""
    import subprocess
    
    # Calculate target bitrate (rough estimate: bitrate = size * 8 / duration)
    # Assume ~90 seconds for 3 segments
    duration = 90
    target_bitrate_kbps = int((target_size_mb * 8 * 1024) / duration)
    
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-c:v", "libx264", "-preset", "fast", "-crf", "28",  # Higher CRF = smaller file
        "-maxrate", f"{target_bitrate_kbps}k", "-bufsize", f"{target_bitrate_kbps * 2}k",
        "-c:a", "aac", "-b:a", "96k",  # Lower audio bitrate
        "-movflags", "+faststart",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg compression failed: {result.stderr.decode()}")
    return output_path

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

def start_pipeline(channel: str, out_dir: Path, args):
    """Start streamlink -> ffmpeg pipeline with better segment handling."""
    selected_quality = args.quality or DEFAULT_STREAM_QUALITY or "best"
    # Removed deprecated --twitch-disable-ads flag (causes PersistedQueryNotFound error)
    # Enhanced streamlink options for better reliability
    sl_cmd = [
        "streamlink",
        "--stream-segment-attempts", "3",  # Retry failed segments
        "--stream-segment-threads", "1",  # Single thread for stability
        "--stream-segment-timeout", "10",  # Timeout for segments (fixed: was --hls-segment-timeout)
        "--stream-timeout", "30",  # Overall timeout (fixed: was --hls-timeout)
        f"https://twitch.tv/{channel}", 
        selected_quality, 
        "-O"
    ]
    seg_pattern = str(out_dir / "seg_%05d.mp4")
    resolved_encoder = resolve_encoder(args.encoder)
    ff_cmd = build_ffmpeg_command(
        seg_pattern,
        resolved_encoder,
        args.video_bitrate,
        args.audio_bitrate,
        args.scale_width
    )

    # Create log files for debugging
    # Windows-compatible log directory
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    sl_log = log_dir / f"streamlink_{channel}.log"
    ff_log = log_dir / f"ffmpeg_{channel}.log"
    
    print(f"🔧 Starting pipeline for {channel}...", flush=True)
    print(f"📝 Streamlink log: {sl_log}", flush=True)
    print(f"📝 FFmpeg log: {ff_log}", flush=True)
    
    # Open log files for writing
    sl_log_handle = open(sl_log, 'a')
    ff_log_handle = open(ff_log, 'a')
    
    p_sl = subprocess.Popen(
        sl_cmd, 
        stdout=subprocess.PIPE,
        stderr=sl_log_handle,
        bufsize=1
    )
    p_ff = subprocess.Popen(
        ff_cmd, 
        stdin=p_sl.stdout,
        stderr=ff_log_handle,
        bufsize=1
    )
    p_sl.stdout.close()
    
    # Give processes a moment to start
    time.sleep(1)
    
    # Check if processes started successfully
    if p_sl.poll() is not None:
        print(f"❌ Streamlink died immediately with exit code {p_sl.poll()}", flush=True)
        raise RuntimeError(f"Streamlink failed to start. Check {sl_log}")
    if p_ff.poll() is not None:
        print(f"❌ FFmpeg died immediately with exit code {p_ff.poll()}", flush=True)
        raise RuntimeError(f"FFmpeg failed to start. Check {ff_log}")
    
    print(f"✅ Pipeline started: streamlink PID {p_sl.pid}, ffmpeg PID {p_ff.pid}", flush=True)
    return p_sl, p_ff, seg_pattern
def wait_for_file_complete(file_path: Path, stable_time: float = 8.0, check_interval: float = 0.5, max_wait: float = 60.0) -> bool:
    """Wait for file to be completely written by checking multiple indicators, with a timeout."""
    if not file_path.exists():
        return False
    
    start_time = time.time()
    last_size = -1
    last_mtime = -1
    stable_counter = 0
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait:
            print(f"⚠️ Timeout ({max_wait}s) waiting for {file_path.name} to stabilize", flush=True)
            return False
        
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
 

def validate_mp4_file(file_path: Path) -> bool:
    """Validate that the MP4 file is properly formatted."""
    try:
        with open(file_path, "rb") as f:
            # Read first 32 bytes to check MP4 signature
            header = f.read(32)
            if len(header) < 32:
                return False
            
            # Check for MP4 signature (ftyp atom)
            if not (header.startswith(b'\x00\x00\x00') and b'ftyp' in header[:32]):
                return False
            
            # Check file size - must be reasonable
            file_size = file_path.stat().st_size
            if file_size < 10000:  # At least 10KB
                return False
            
            # Try to find moov atom - be more lenient
            f.seek(0)
            data = f.read(min(file_size, 1024*1024))  # Read up to 1MB
            if b'moov' not in data:
                # If not in first MB, check the end
                f.seek(-min(file_size, 1024*1024), 2)
                tail = f.read(min(file_size, 1024*1024))
                if b'moov' not in tail:
                    return False
                
            return True
    except Exception:
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
    parser.add_argument("--quality", default=DEFAULT_STREAM_QUALITY, help="Streamlink quality to request (e.g., 720p30).")
    parser.add_argument("--encoder", default=DEFAULT_ENCODER, choices=["auto", "cpu", "videotoolbox", "cuda", "qsv", "copy"], help="FFmpeg encoder to use.")
    parser.add_argument("--video-bitrate", type=int, default=DEFAULT_VIDEO_BITRATE, help="Target video bitrate in kbps when encoding.")
    parser.add_argument("--audio-bitrate", type=int, default=DEFAULT_AUDIO_BITRATE, help="Target audio bitrate in kbps.")
    parser.add_argument("--scale-width", type=int, default=DEFAULT_SCALE_WIDTH, help="Scale video width (set 0 to keep original).")
    args = parser.parse_args()

    os.environ["USE_SERVICE_ROLE"] = "true"
    sb = get_client()
    
    # Windows-compatible temp directory
    if sys.platform == "win32":
        temp_base = os.environ.get("TEMP", os.environ.get("TMP", "C:\\temp"))
        out_dir = Path(tempfile.mkdtemp(prefix=f"live_{args.channel}_", dir=temp_base))
    else:
        out_dir = Path(tempfile.mkdtemp(prefix=f"live_{args.channel}_"))
    
    print(f"📁 Writing temp segments to: {out_dir}")
    
    # Pre-load models once at startup to avoid reloading on every segment
    print("🔄 Pre-loading AI models...", flush=True)
    from select_and_clip import get_whisper_model, get_sentiment_pipeline
    get_whisper_model()  # Load once
    get_sentiment_pipeline()  # Load once
    print("✅ Models pre-loaded and cached", flush=True)

    streams_row = ensure_streams_row(sb, args.channel, args.stream_id, args.user_id)
    stream_uid = streams_row["twitch_stream_id"]
    print(f"🗂 Using streams row id={streams_row['id']} twitch_stream_id={stream_uid}")

    p_sl, p_ff, seg_pattern = start_pipeline(args.channel, out_dir, args)
    print("▶️ Recording... (Ctrl+C to stop)", flush=True)
    print(f"📁 Segment pattern: {seg_pattern}", flush=True)
    print(f"📁 Output directory: {out_dir}", flush=True)
    print(f"🔍 Streamlink PID: {p_sl.pid}, FFmpeg PID: {p_ff.pid}", flush=True)

    known = set()
    interesting_buffer=[]
    iteration_count = 0
    try:
        while True:
            iteration_count += 1
            if iteration_count % 10 == 0:  # Log every 10 iterations
                print(f"🔄 Iteration {iteration_count}: {len(known)} segments processed, {len(interesting_buffer)} in buffer", flush=True)
            
            # Add delay between iterations to reduce CPU load
            time.sleep(0.5)  # 500ms delay between iteration loops
            
            for file in sorted(out_dir.glob("seg_*.mp4")):
                if file not in known and wait_for_file_complete(file, max_wait=60.0):
                    print(f"📹 Processing {file.name}...", flush=True)
                    try:
                        # Add delay to prevent CPU spikes from rapid processing
                        # AI model inference is CPU-intensive, so we throttle processing
                        time.sleep(0.3)  # 300ms delay between segments to reduce CPU load
                        is_interesting = detect_interest(file)
                        if is_interesting:  # Call the function to process the segment
                            interesting_buffer.append(Path(file))
                            print(f"🔥 Added to buffer ({len(interesting_buffer)}/5): {file.name}", flush=True)
                        else:
                            print(f"⏭️ Skipped (not interesting): {file.name}", flush=True)
                            known.add(file)
                            safe_delete(file)
                    except Exception as e:
                        print(f"❌ Error processing {file.name}: {e}", flush=True)
                        import traceback
                        traceback.print_exc()
                        known.add(file)  # Mark as processed even on error
                        continue
                    
                    known.add(file)
                    
                    # If 5 interesting clips collected
                    if len(interesting_buffer) >= 5:
                        try:
                            merged_path = out_dir / f"merged_{int(time.time())}.mp4"
                            top_segments = select_best_segments([str(p) for p in interesting_buffer], top_k=3)
                            top_segment_paths = [Path(s[0]) for s in top_segments]

                            merge_segments(top_segment_paths, merged_path)
                            video_bytes = read_file_safely(merged_path)
                            
                            # Check file size before upload (Supabase limit is ~50-100MB)
                            file_size_mb = len(video_bytes) / (1024 * 1024)
                            if file_size_mb > 45:  # Safety margin below 50MB limit
                                print(f"⚠️ Merged clip too large ({file_size_mb:.1f} MB), compressing...", flush=True)
                                # Re-encode with lower bitrate to reduce size
                                compressed_path = out_dir / f"compressed_{int(time.time())}.mp4"
                                compress_video(merged_path, compressed_path, target_size_mb=40)
                                video_bytes = read_file_safely(compressed_path)
                                merged_path = compressed_path
                                print(f"✅ Compressed to {len(video_bytes) / (1024 * 1024):.1f} MB", flush=True)
                            
                            key = upload_segment(sb, args.bucket, video_bytes, args.prefix, args.channel, stream_uid)
                            print(f"⬆️ Uploaded merged clip: {key}", flush=True)
                            
                            # Insert clip into clips_metadata table
                            try:
                                user_id = os.getenv('MONITOR_USER_ID') or args.user_id
                                if not user_id:
                                    print("⚠️ No user_id found, skipping database insert", flush=True)
                                else:
                                    # Get storage URL
                                    storage_url = sb.storage.from_(args.bucket).get_public_url(key)
                                    
                                    # Calculate average confidence score from top segments
                                    avg_score = sum(s[1] for s in top_segments) / len(top_segments) if top_segments else 0.5
                                    
                                    # Get transcript from segments (combine all transcripts)
                                    transcript = " ".join([s[2] for s in top_segments if s[2]]).strip()
                                    
                                    # Calculate average scoring breakdown from top segments (Past Backend Format)
                                    avg_energy = sum(s[3].get('energy', 0) for s in top_segments) / len(top_segments) if top_segments else 0
                                    avg_pitch = sum(s[3].get('pitch', 0) for s in top_segments) / len(top_segments) if top_segments else 0
                                    avg_emotion = sum(s[3].get('emotion', 0) for s in top_segments) / len(top_segments) if top_segments else 0
                                    avg_keyword = sum(s[3].get('keyword', 0) for s in top_segments) / len(top_segments) if top_segments else 0
                                    
                                    # Create scoring breakdown in past backend format (concise, single-line)
                                    details_dict = {
                                        'energy': round(avg_energy, 4),
                                        'pitch': round(avg_pitch, 4),
                                        'emotion': round(avg_emotion, 4),
                                        'keyword': round(avg_keyword, 2)
                                    }
                                    
                                    # Past backend format: "Score: X.XXX | {details} | Transcript"
                                    hype_indicator = " 🔥" if avg_keyword > 0 else ""
                                    scoring_line = f"Score: {avg_score:.3f} | {details_dict}{hype_indicator}\n"
                                    
                                    # Combine scoring with transcript (past backend style)
                                    full_transcript = scoring_line + (transcript or f"Clip from {args.channel}")
                                    
                                    # Print scoring breakdown to console (past backend format)
                                    print(f"\n🎧 Clip created | Score: {avg_score:.3f} | {details_dict}{hype_indicator}", flush=True)
                                    print(f"   Transcript: {transcript[:80] if transcript else 'N/A'}...\n", flush=True)
                                    
                                    # Insert into clips_metadata
                                    clip_data = {
                                        'user_id': user_id,
                                        'channel_name': args.channel,
                                        'stream_id': stream_uid,
                                        'storage_url': storage_url,
                                        'storage_path': key,
                                        'file_size': len(video_bytes),
                                        'confidence_score': avg_score,
                                        'transcript': full_transcript,
                                        'created_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
                                    }
                                    
                                    result = sb.table('clips_metadata').insert(clip_data).execute()
                                    if result.data:
                                        print(f"✅ Inserted clip into database: {result.data[0].get('id')}", flush=True)
                                    else:
                                        print("⚠️ Failed to insert clip into database", flush=True)
                            except Exception as e:
                                print(f"⚠️ Error inserting clip into database: {e}", flush=True)
                                import traceback
                                traceback.print_exc()
                                # Continue even if DB insert fails

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
                            print(f"❌ Failed to merge batch: {e}", flush=True)
                            import traceback
                            traceback.print_exc()
                            # Clear buffer even on failure to prevent accumulation
                            # Keep only the most recent 2 segments to retry next time
                            if len(interesting_buffer) > 2:
                                for seg in interesting_buffer[:-2]:
                                    safe_delete(seg)
                                    if seg in known:
                                        known.remove(seg)
                                interesting_buffer = interesting_buffer[-2:]
                                print(f"⚠️ Cleared buffer, keeping last 2 segments for retry", flush=True)
                            # Don't clear buffer if error, try next iteration
                            
            # Adaptive sleep: longer when no segments found, shorter when processing
            segments_found = len([f for f in out_dir.glob("seg_*.mp4") if f not in known])
            all_segments = list(out_dir.glob("seg_*.mp4"))
            if segments_found == 0:
                # Check if streamlink/ffmpeg processes are still alive
                sl_status = p_sl.poll()
                ff_status = p_ff.poll()
                if sl_status is not None or ff_status is not None:
                    print(f"⚠️ Streamlink or FFmpeg process died! streamlink={sl_status}, ffmpeg={ff_status}", flush=True)
                    # Restart pipeline
                    print("🔄 Restarting pipeline...", flush=True)
                    p_sl, p_ff, seg_pattern = start_pipeline(args.channel, out_dir, args)
                    known.clear()  # Reset known files
                    interesting_buffer.clear()  # Reset buffer
                elif iteration_count % 100 == 0:  # Log diagnostics every 100 iterations
                    print(f"🔍 Diagnostics: {len(all_segments)} total segments in {out_dir}, {len(known)} known, {segments_found} new", flush=True)
                    if len(all_segments) > 0:
                        print(f"📹 Sample segments: {[f.name for f in all_segments[:3]]}", flush=True)
                time.sleep(5)  # Longer sleep when idle (5s instead of 2s) - reduces CPU usage
            else:
                time.sleep(2)  # Normal sleep when segments are being created

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
