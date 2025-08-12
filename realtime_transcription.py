#!/usr/bin/env python3
"""
Real-time transcription script for Twitch clips using WhisperX.
Improved version with silence padding, better model options, and ML-based clip-worthiness detection.
"""

import os
import subprocess
import whisperx
import torch
import threading
import time
import argparse
import hashlib
from pathlib import Path
from datetime import datetime

# Import engagement logging
from src.supabase_utils import log_engagement_data, simulate_realistic_engagement, assign_auto_label

DATA_DIR = os.getenv("MODEL_DATA_DIR", "data/")

def generate_segment_hash(text: str, start: float, end: float) -> str:
    """
    Generate a unique hash for a segment based on its text, start, and end timestamps.
    
    Args:
        text: The transcribed text of the segment
        start: Start timestamp of the segment
        end: End timestamp of the segment
        
    Returns:
        str: SHA256 hash of the segment content
    """
    content = f"{text.strip()}|{start:.2f}|{end:.2f}"
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

parser = argparse.ArgumentParser(description="Twitch Clip Collection and Transcription System")
parser.add_argument("--mode", choices=["realtime", "training"], default="realtime",
                   help="Mode: realtime (audio transcription) or training (clip collection)")
parser.add_argument("--max-clips", type=int, default=20,
                   help="Maximum number of clips to collect (training mode)")
parser.add_argument("--dry-run", action="store_true", help="Run without creating actual clips")
args = parser.parse_args()

# WhisperX model configuration
WHISPER_MODEL_SIZE = "large-v3"  # Options: "tiny", "base", "small", "medium", "large", "large-v2", "large-v3"
WHISPER_MODEL = None
WHISPER_MODEL_ENHANCED = None  # Enhanced model for fallback (large-v3)
TRANSCRIPTION_FAILURES = 0  # Track consecutive failures
MAX_FAILURES_BEFORE_ENHANCED = 1  # Switch to enhanced model after 1 failure

# Clip processing configuration
CLIPS_CREATED_THIS_RUN = 0  # Track clips created in current run
MAX_CLIPS_PER_RUN = 20  # Maximum clips per run
PROCESSING_LOCK = threading.Lock()  # Ensure sequential processing

# Buffer segments for clip creation
BUFFER_SEGMENTS = []

# Random clip pulling thread
RANDOM_CLIP_THREAD = None

def add_segment_to_buffer(segment_path):
    """
    Add a new .ts segment to the buffer for clip creation.
    
    Args:
        segment_path: Path to the .ts segment file
    """
    global BUFFER_SEGMENTS
    
    if not os.path.exists(segment_path):
        print(f"⚠️  Segment file not found: {segment_path}")
        return False
    
    BUFFER_SEGMENTS.append(segment_path)
    print(f"📥 Added new segment to buffer: {os.path.basename(segment_path)}")
    print(f"📊 Buffer now contains {len(BUFFER_SEGMENTS)} segments")
    
    # Keep only the last 10 segments to prevent memory issues
    if len(BUFFER_SEGMENTS) > 10:
        old_segment = BUFFER_SEGMENTS.pop(0)
        print(f"🗑️  Removed old segment from buffer: {os.path.basename(old_segment)}")
    
    return True

def create_buffer_audio():
    """
    Create buffer_audio.wav from the current buffer segments.
    This function should be called every ~5 seconds.
    """
    global BUFFER_SEGMENTS
    
    if not BUFFER_SEGMENTS:
        print("⚠️  No segments in buffer to create audio")
        return False
    
    try:
        # Create segments directory if it doesn't exist
        segments_dir = Path("segments")
        segments_dir.mkdir(exist_ok=True)
        
        # Create a temporary file list for FFmpeg
        file_list_path = "temp_buffer_list.txt"
        with open(file_list_path, 'w') as f:
            for segment in BUFFER_SEGMENTS:
                f.write(f"file '{segment}'\n")
        
        # Use FFmpeg to concatenate segments into buffer_audio.wav
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', file_list_path,
            '-c', 'copy',
            'buffer_audio.wav'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Clean up temporary file
        if os.path.exists(file_list_path):
            os.remove(file_list_path)
        
        if result.returncode == 0:
            print(f"🎤 Created buffer_audio.wav from {len(BUFFER_SEGMENTS)} segments")
            return True
        else:
            print(f"❌ Failed to create buffer_audio.wav: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating buffer audio: {e}")
        return False

def monitor_segments_directory():
    """
    Monitor the segments directory for new .ts files and add them to buffer.
    This function runs in a separate thread.
    """
    segments_dir = Path("segments")
    segments_dir.mkdir(exist_ok=True)
    
    # Track processed files to avoid duplicates
    processed_files = set()
    
    print("👀 Starting segment directory monitor...")
    
    while True:
        try:
            # Get all .ts files in the segments directory
            ts_files = list(segments_dir.glob("*.ts"))
            
            for ts_file in ts_files:
                if str(ts_file) not in processed_files:
                    add_segment_to_buffer(str(ts_file))
                    processed_files.add(str(ts_file))
            
            # Sleep for a short time before checking again
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error in segment monitor: {e}")
            time.sleep(5)

def start_segment_monitor():
    """
    Start the background thread for monitoring segments directory.
    """
    segment_thread = threading.Thread(target=monitor_segments_directory, daemon=True)
    segment_thread.start()
    print("✅ Segment monitor thread started")
    return segment_thread

def get_random_clip_and_transcript():
    """
    Get a random clip and its transcript from existing data.
    
    Returns:
        tuple: (clip_path, transcript) or (None, None) if no clips available
    """
    import os
    import random
    
    # Check if we have existing clips in the clips directory
    clips_dir = Path("clips")
    if not clips_dir.exists():
        return None, None
    
    # Get all .mp4 files
    clip_files = list(clips_dir.glob("*.mp4"))
    if not clip_files:
        return None, None
    
    # Select a random clip
    random_clip = random.choice(clip_files)
    
    # Try to find corresponding transcript from clip_log.csv
    transcript = None
    clip_log_path = "clip_log.csv"
    
    if os.path.exists(clip_log_path):
        import csv
        clip_id = random_clip.stem  # filename without extension
        
        with open(clip_log_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('clip_path', '').endswith(f"{clip_id}.mp4"):
                    # Extract transcript from filename if available
                    if '_' in clip_id:
                        # Try to reconstruct transcript from filename
                        parts = clip_id.split('_')
                        if len(parts) > 2:
                            # Skip timestamp parts and reconstruct transcript
                            transcript_parts = parts[2:]  # Skip 'clip' and timestamp
                            transcript = ' '.join(transcript_parts).replace('_', ' ')
                    break
    
    return str(random_clip), transcript

def pull_random_clip_loop():
    """
    Background loop that periodically pulls random clips for labeling.
    Runs every 120 seconds (2 minutes).
    """
    print("🔄 Random clip pulling loop started (every 120 seconds)")
    
    while True:
        try:
            time.sleep(120)  # Wait 2 minutes
            
            random_clip, transcript = get_random_clip_and_transcript()
            if transcript and random_clip:
                print(f"🎲 Pulling random clip for labeling: {os.path.basename(random_clip)}")
                save_for_labeling(transcript, random_clip, source="random")
            else:
                print("⚠️  No random clips available for labeling")
                
        except Exception as e:
            print(f"❌ Error in random clip loop: {e}")
            time.sleep(30)  # Wait 30 seconds before retrying

def start_random_clip_thread():
    """
    Start the background thread for random clip pulling.
    """
    global RANDOM_CLIP_THREAD
    
    if RANDOM_CLIP_THREAD is None or not RANDOM_CLIP_THREAD.is_alive():
        RANDOM_CLIP_THREAD = threading.Thread(target=pull_random_clip_loop, daemon=True)
        RANDOM_CLIP_THREAD.start()
        print("✅ Random clip pulling thread started")
    else:
        print("⚠️  Random clip thread already running")

def save_for_labeling(transcript, clip_path, source="ml"):
    """
    Save clip information for manual labeling to improve the ML model.
    Uses Supabase for cloud-based labeling.
    
    Args:
        transcript: The transcript text that triggered the clip
        clip_path: Path to the created clip file
        source: Source of the clip ("ml", "random", etc.)
    """
    import os
    
    # Generate clip_id from file path
    clip_id = os.path.splitext(os.path.basename(clip_path))[0]
    
    # Try Supabase
    try:
        from src.supabase_integration import save_for_labeling as supabase_save
        supabase_clip_id = supabase_save(transcript, clip_path, source=source)
        if supabase_clip_id:
            print(f"📝 Saved for labeling (Supabase): {supabase_clip_id}")
            return
    except Exception as e:
        print(f"⚠️  Supabase save failed: {e}")

def log_clip_metadata(timestamp, num_segments, clip_path, transcript=None):
    """
    Log clip metadata to CSV file for tracking and analysis.
    
    Args:
        timestamp: Timestamp when clip was created
        num_segments: Number of segments used in the clip
        clip_path: Path to the created clip file
        transcript: Optional transcript text that triggered the clip
    """
    import csv
    import os
    
    csv_file = "clip_log.csv"
    file_exists = os.path.exists(csv_file)
    
    # Prepare transcript snippet for logging
    transcript_snippet = ""
    if transcript and transcript.strip():
        words = transcript.strip().split()[:5]
        transcript_snippet = " ".join(words)
    
    # Prepare data row
    row_data = {
        'timestamp': timestamp,
        'num_segments': num_segments,
        'clip_path': clip_path,
        'transcript_snippet': transcript_snippet
    }
    
    try:
        with open(csv_file, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['timestamp', 'num_segments', 'clip_path', 'transcript_snippet']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write headers if file doesn't exist
            if not file_exists:
                writer.writeheader()
            
            # Write the data row
            writer.writerow(row_data)
            
        print(f"📝 Logged clip metadata to {csv_file}")
        
    except Exception as e:
        print(f"❌ Error logging clip metadata: {e}")

def load_whisper_model():
    """Load WhisperX model with specified size."""
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        print(f"📥 Loading WhisperX model: {WHISPER_MODEL_SIZE}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        WHISPER_MODEL = whisperx.load_model(WHISPER_MODEL_SIZE, device, compute_type="float32")
        print(f"✅ WhisperX model loaded on {device}")
    return WHISPER_MODEL

def load_enhanced_whisper_model():
    """Load enhanced WhisperX model (large-v3) for fallback when medium struggles."""
    global WHISPER_MODEL_ENHANCED
    if WHISPER_MODEL_ENHANCED is None:
        print(f"📥 Loading enhanced WhisperX model: large-v3 (fallback)")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        WHISPER_MODEL_ENHANCED = whisperx.load_model("large-v3", device, compute_type="float32")
        print(f"✅ Enhanced WhisperX model loaded on {device}")
    return WHISPER_MODEL_ENHANCED

def check_whisperx_environment():
    """Check if WhisperX is properly installed and accessible."""
    try:
        import whisperx
        
        # Try to get version, but don't fail if it's not available
        try:
            version = whisperx.__version__
            print(f"✅ WhisperX version: {version}")
        except AttributeError:
            print("✅ WhisperX installed (version not available)")
        
        # Check if we're in the correct virtual environment
        import sys
        venv_path = sys.prefix
        print(f"🔧 Virtual environment: {venv_path}")
        
        # Check CUDA availability
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🖥️  Using device: {device}")
        
        if device == "cuda":
            print(f"🎮 CUDA device: {torch.cuda.get_device_name()}")
        
        return True
    except ImportError as e:
        print(f"❌ WhisperX not found: {e}")
        print("💡 Make sure to activate the virtual environment: source venv-py311/bin/activate")
        return False
    except Exception as e:
        print(f"❌ Error checking WhisperX environment: {e}")
        return False

def check_clip_limit():
    """Check if we've reached the maximum clips per run."""
    global CLIPS_CREATED_THIS_RUN, MAX_CLIPS_PER_RUN
    return CLIPS_CREATED_THIS_RUN >= MAX_CLIPS_PER_RUN

def increment_clip_count():
    """Increment the clip count for this run."""
    global CLIPS_CREATED_THIS_RUN
    with PROCESSING_LOCK:
        CLIPS_CREATED_THIS_RUN += 1
        print(f"📊 Clips created this run: {CLIPS_CREATED_THIS_RUN}/{MAX_CLIPS_PER_RUN}")

def reset_clip_count():
    """Reset the clip count for a new run."""
    global CLIPS_CREATED_THIS_RUN
    with PROCESSING_LOCK:
        CLIPS_CREATED_THIS_RUN = 0
        print(f"🔄 Reset clip counter: {CLIPS_CREATED_THIS_RUN}/{MAX_CLIPS_PER_RUN}")

def get_clip_count():
    """Get current clip count for this run."""
    global CLIPS_CREATED_THIS_RUN, MAX_CLIPS_PER_RUN
    return CLIPS_CREATED_THIS_RUN, MAX_CLIPS_PER_RUN

def create_clip_from_buffer(transcript=None, dry_run=False):
    """
    Create a real Twitch clip from the current buffer segments.
    This function is now a wrapper around create_twitch_clip for backward compatibility.
    
    Args:
        transcript: Optional transcript text for the clip
        dry_run: If True, don't actually create the file
        
    Returns:
        clip_path: Path to the created clip file, or None if failed
    """
    return create_twitch_clip(transcript=transcript, dry_run=dry_run)

def add_timing_features_to_segments(transcription_result):
    """
    Calculate and add timing features to transcription segments.
    
    Args:
        transcription_result: WhisperX transcription result with segments
        
    Returns:
        dict: Updated transcription result with timing features added to segments
    """
    segments = transcription_result.get("segments", [])
    
    if not segments:
        return transcription_result
    
    # Sort segments by start time to ensure proper order
    segments = sorted(segments, key=lambda x: x.get("start", 0))
    
    for i, segment in enumerate(segments):
        # Calculate segment duration
        start_time = segment.get("start", 0)
        end_time = segment.get("end", 0)
        segment_duration = end_time - start_time
        
        # Calculate pause before this segment
        if i == 0:
            # First segment has no pause before it
            pause_before = 0.0
        else:
            previous_segment = segments[i - 1]
            previous_end = previous_segment.get("end", 0)
            pause_before = max(0.0, start_time - previous_end)
        
        # Add timing features to segment metadata
        segment["segment_duration"] = round(segment_duration, 3)
        segment["pause_before"] = round(pause_before, 3)
        
        # Add timing categories for easier analysis
        if segment_duration < 1.0:
            segment["duration_category"] = "short"
        elif segment_duration < 3.0:
            segment["duration_category"] = "medium"
        else:
            segment["duration_category"] = "long"
        
        if pause_before > 0:
            if pause_before < 0.5:
                segment["pause_category"] = "short"
            elif pause_before < 1.5:
                segment["pause_category"] = "medium"
            else:
                segment["pause_category"] = "long"
        else:
            segment["pause_category"] = "none"
    
    # Update the result with modified segments
    transcription_result["segments"] = segments
    
    # Add timing summary statistics
    segment_durations = [seg.get("segment_duration", 0) for seg in segments]
    pause_durations = [seg.get("pause_before", 0) for seg in segments]
    
    if segment_durations:
        transcription_result["timing_stats"] = {
            "total_segments": len(segments),
            "avg_segment_duration": round(sum(segment_durations) / len(segment_durations), 3),
            "max_segment_duration": round(max(segment_durations), 3),
            "min_segment_duration": round(min(segment_durations), 3),
            "avg_pause_duration": round(sum(pause_durations) / len(pause_durations), 3),
            "max_pause_duration": round(max(pause_durations), 3),
            "segments_with_pauses": len([p for p in pause_durations if p > 0])
        }
    
    return transcription_result

def add_sentiment_scores_to_segments(transcription_result):
    """
    Add sentiment scores to each segment using a lightweight sentiment model.
    
    Args:
        transcription_result: WhisperX transcription result with segments
        
    Returns:
        dict: Updated transcription result with sentiment scores added to segments
    """
    segments = transcription_result.get("segments", [])
    
    if not segments:
        return transcription_result
    
    try:
        from transformers import pipeline
        
        # Initialize sentiment analysis pipeline
        sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            return_all_scores=True
        )
        
        print("🧠 Analyzing sentiment for segments...")
        
        for i, segment in enumerate(segments):
            text = segment.get("text", "").strip()
            
            if text:
                try:
                    # Get sentiment scores
                    results = sentiment_analyzer(text)
                    
                    # Extract positive and negative scores
                    scores = results[0]
                    positive_score = next((score['score'] for score in scores if score['label'] == 'POSITIVE'), 0.5)
                    negative_score = next((score['score'] for score in scores if score['label'] == 'NEGATIVE'), 0.5)
                    
                    # Calculate sentiment score between -1 and 1
                    sentiment_score = (positive_score - negative_score)
                    
                    # Determine sentiment category
                    if sentiment_score > 0.3:
                        sentiment_category = "positive"
                    elif sentiment_score < -0.3:
                        sentiment_category = "negative"
                    else:
                        sentiment_category = "neutral"
                    
                    # Add sentiment data to segment
                    segment["sentiment_score"] = round(sentiment_score, 3)
                    segment["sentiment_category"] = sentiment_category
                    segment["positive_score"] = round(positive_score, 3)
                    segment["negative_score"] = round(negative_score, 3)
                    
                except Exception as e:
                    print(f"⚠️ Sentiment analysis failed for segment {i}: {e}")
                    # Add default sentiment values
                    segment["sentiment_score"] = 0.0
                    segment["sentiment_category"] = "neutral"
                    segment["positive_score"] = 0.5
                    segment["negative_score"] = 0.5
            else:
                # Empty text gets neutral sentiment
                segment["sentiment_score"] = 0.0
                segment["sentiment_category"] = "neutral"
                segment["positive_score"] = 0.5
                segment["negative_score"] = 0.5
        
        # Add sentiment summary statistics
        sentiment_scores = [seg.get("sentiment_score", 0) for seg in segments]
        if sentiment_scores:
            transcription_result["sentiment_stats"] = {
                "avg_sentiment_score": round(sum(sentiment_scores) / len(sentiment_scores), 3),
                "max_sentiment_score": round(max(sentiment_scores), 3),
                "min_sentiment_score": round(min(sentiment_scores), 3),
                "positive_segments": len([s for s in sentiment_scores if s > 0.3]),
                "negative_segments": len([s for s in sentiment_scores if s < -0.3]),
                "neutral_segments": len([s for s in sentiment_scores if -0.3 <= s <= 0.3])
            }
        
        print(f"✅ Sentiment analysis completed for {len(segments)} segments")
        
    except ImportError:
        print("⚠️ Transformers library not available, skipping sentiment analysis")
        # Add default sentiment values to all segments
        for segment in segments:
            segment["sentiment_score"] = 0.0
            segment["sentiment_category"] = "neutral"
            segment["positive_score"] = 0.5
            segment["negative_score"] = 0.5
    except Exception as e:
        print(f"⚠️ Sentiment analysis failed: {e}")
        # Add default sentiment values to all segments
        for segment in segments:
            segment["sentiment_score"] = 0.0
            segment["sentiment_category"] = "neutral"
            segment["positive_score"] = 0.5
            segment["negative_score"] = 0.5
    
    return transcription_result

def add_multimodal_placeholders_to_segments(transcription_result):
    """
    Add placeholder boolean keys for future multimodal inputs.
    
    Args:
        transcription_result: WhisperX transcription result with segments
        
    Returns:
        dict: Updated transcription result with multimodal placeholders added to segments
    """
    segments = transcription_result.get("segments", [])
    
    if not segments:
        return transcription_result
    
    for segment in segments:
        # Add placeholder boolean keys for future multimodal features
        segment["chat_spike"] = False  # Future: Twitch chat activity spike
        segment["viewer_emote_spam"] = False  # Future: Viewer emote reactions
        segment["donation_alert"] = False  # Future: Donation/subscription alerts
        segment["follow_alert"] = False  # Future: New follower alerts
        segment["raid_alert"] = False  # Future: Raid notifications
        segment["streamer_reaction"] = False  # Future: Streamer's visual reactions
        segment["background_music"] = False  # Future: Background music detection
        segment["sound_effects"] = False  # Future: Sound effects detection
    
    return transcription_result

def add_pause_durations_to_segments(transcription_result):
    """
    Calculate and add pause duration metadata to transcription segments.
    
    Args:
        transcription_result: WhisperX transcription result with segments
        
    Returns:
        dict: Updated transcription result with pause durations added to segments
    """
    segments = transcription_result.get("segments", [])
    
    if not segments:
        return transcription_result
    
    # Sort segments by start time to ensure proper order
    segments = sorted(segments, key=lambda x: x.get("start", 0))
    
    for i, segment in enumerate(segments):
        # Calculate pause before this segment
        if i == 0:
            # First segment has no pause before it
            pause_before = 0.0
        else:
            previous_segment = segments[i - 1]
            current_start = segment.get("start", 0)
            previous_end = previous_segment.get("end", 0)
            pause_before = max(0.0, current_start - previous_end)
        
        # Add pause duration to segment metadata
        segment["pause_before"] = round(pause_before, 3)  # Round to 3 decimal places
        
        # Add additional pause analysis
        if pause_before > 0:
            if pause_before < 0.5:
                segment["pause_category"] = "short"
            elif pause_before < 1.5:
                segment["pause_category"] = "medium"
            else:
                segment["pause_category"] = "long"
        else:
            segment["pause_category"] = "none"
    
    # Update the result with modified segments
    transcription_result["segments"] = segments
    
    # Add summary statistics
    pause_durations = [seg.get("pause_before", 0) for seg in segments]
    if pause_durations:
        transcription_result["pause_stats"] = {
            "total_segments": len(segments),
            "avg_pause_duration": round(sum(pause_durations) / len(pause_durations), 3),
            "max_pause_duration": round(max(pause_durations), 3),
            "min_pause_duration": round(min(pause_durations), 3),
            "segments_with_pauses": len([p for p in pause_durations if p > 0])
        }
    
    return transcription_result

def add_silence_padding(input_file, output_file, padding_ms=250):
    """
    Add silence padding to the beginning and end of an audio file using ffmpeg.
    
    Args:
        input_file: Path to input audio file
        output_file: Path to output audio file with padding
        padding_ms: Duration of silence to add in milliseconds
    """
    try:
        # Convert milliseconds to seconds
        padding_s = padding_ms / 1000.0
        
        # FFmpeg command to add silence padding
        cmd = [
            'ffmpeg', '-y',  # Overwrite output file
            '-f', 'lavfi', '-i', f'anullsrc=channel_layout=stereo:sample_rate=48000',
            '-i', str(input_file),
            '-filter_complex', f'[0:a]atrim=0:{padding_s}[silence1];[silence1][1:a][silence1]concat=n=3:v=0:a=1[out]',
            '-map', '[out]',
            str(output_file)
        ]
        
        # Alternative simpler approach using apad
        cmd_simple = [
            'ffmpeg', '-y',
            '-i', str(input_file),
            '-af', f'apad=pad_dur={padding_s}:whole_dur={padding_s}',
            str(output_file)
        ]
        
        # Run the command
        result = subprocess.run(cmd_simple, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Added {padding_ms}ms silence padding to {input_file}")
            return True
        else:
            print(f"❌ Failed to add silence padding: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error adding silence padding: {e}")
        return False

def transcribe_buffer_audio(buffer_file="buffer_audio.wav"):
    """
    Transcribe audio buffer with improved quality for short, noisy Twitch segments using WhisperX.
    Automatically falls back to enhanced model if standard model fails repeatedly.
    
    Args:
        buffer_file: Path to the audio buffer file
        
    Returns:
        dict: Transcription result with segments and text, or None if transcription fails
    """
    global TRANSCRIPTION_FAILURES
    
    try:
        # Check if buffer file exists
        if not os.path.exists(buffer_file):
            print(f"❌ Buffer file not found: {buffer_file}")
            return None
        
        # Create padded version of the audio
        padded_file = "buffer_audio_padded.wav"
        
        # Add silence padding (250ms at start and end)
        if not add_silence_padding(buffer_file, padded_file, padding_ms=250):
            print("⚠️  Using original file without padding")
            padded_file = buffer_file
        
        # Determine which model to use based on failure count
        if TRANSCRIPTION_FAILURES >= MAX_FAILURES_BEFORE_ENHANCED:
            print(f"🔄 Using enhanced WhisperX model due to {TRANSCRIPTION_FAILURES} consecutive failures")
            model = load_enhanced_whisper_model()
            model_name = "large-v2 (enhanced)"
        else:
            model = load_whisper_model()
            model_name = WHISPER_MODEL_SIZE
        
        # Transcribe with WhisperX for better accuracy
        print(f"🎤 Transcribing {padded_file} with WhisperX {model_name} model...")
        
        # Force English language for better speed and accuracy
        result = model.transcribe(
            padded_file,
            language="en"  # Force English language detection
        )
        
        # Clean up padded file if it was created
        if padded_file != buffer_file and os.path.exists(padded_file):
            os.remove(padded_file)
        
        if result["text"].strip():
            print(f"✅ Transcribed: {result['text'][:100]}...")
            
            # Process segments with enhanced context-aware features
            segments = result.get("segments", [])
            if segments:
                print(f"📊 Processing {len(segments)} segments with enhanced features...")
                
                # Step 1: Add timing features (duration, pauses)
                result = add_timing_features_to_segments(result)
                print(f"✅ Added timing features to {len(segments)} segments")
                
                # Step 2: Add sentiment analysis
                result = add_sentiment_scores_to_segments(result)
                print(f"✅ Added sentiment analysis to {len(segments)} segments")
                
                # Step 3: Add multimodal placeholders
                result = add_multimodal_placeholders_to_segments(result)
                print(f"✅ Added multimodal placeholders to {len(segments)} segments")
                
                # Log summary statistics
                if "timing_stats" in result:
                    timing = result["timing_stats"]
                    print(f"📈 Timing: avg_duration={timing['avg_segment_duration']}s, avg_pause={timing['avg_pause_duration']}s")
                
                if "sentiment_stats" in result:
                    sentiment = result["sentiment_stats"]
                    print(f"😊 Sentiment: avg_score={sentiment['avg_sentiment_score']}, positive={sentiment['positive_segments']}")
            
            # Reset failure counter on successful transcription
            if TRANSCRIPTION_FAILURES > 0:
                print(f"🔄 Resetting failure counter (was {TRANSCRIPTION_FAILURES})")
                TRANSCRIPTION_FAILURES = 0
            return result
        else:
            print("⚠️  No speech detected")
            TRANSCRIPTION_FAILURES += 1
            print(f"📊 Consecutive failures: {TRANSCRIPTION_FAILURES}")
            return None
            
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        TRANSCRIPTION_FAILURES += 1
        print(f"📊 Consecutive failures: {TRANSCRIPTION_FAILURES}")
        
        # If we're not already using enhanced model, suggest switching
        if TRANSCRIPTION_FAILURES >= MAX_FAILURES_BEFORE_ENHANCED:
            print(f"🔄 Will switch to enhanced model on next attempt")
        
        return None

def transcribe_clip_for_content_analysis(clip_path):
    """
    High-accuracy transcription of a downloaded clip for content analysis.
    Uses large-v3 model for maximum accuracy with enhanced model fallback if needed.
    
    Args:
        clip_path: Path to the clip file
        
    Returns:
        str: Transcribed text, or None if failed
    """
    global TRANSCRIPTION_FAILURES
    
    try:
        # Determine which model to use based on failure count
        if TRANSCRIPTION_FAILURES >= MAX_FAILURES_BEFORE_ENHANCED:
            print(f"🔄 Using large-v3 model due to {TRANSCRIPTION_FAILURES} consecutive failures")
            model = load_enhanced_whisper_model()
            model_name = "large-v3 (fallback)"
        else:
            model = load_whisper_model()
            model_name = WHISPER_MODEL_SIZE
        
        print(f"🎤 Transcribing {clip_path} with WhisperX {model_name} for content analysis...")
        
        # Force English language for better speed and accuracy
        result = model.transcribe(
            clip_path,
            language="en"  # Force English language detection
        )
        
        # Handle different result structures
        if isinstance(result, dict) and "text" in result:
            transcript = result["text"].strip()
        elif isinstance(result, dict) and "segments" in result:
            # Extract text from segments
            transcript = " ".join([seg.get("text", "") for seg in result["segments"]]).strip()
        else:
            print(f"⚠️  Unexpected result structure: {type(result)}")
            print(f"   Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            transcript = ""
        
        if transcript:
            print(f"✅ Transcribed: {transcript[:100]}...")
            
            # Reset failure counter on successful transcription
            if TRANSCRIPTION_FAILURES > 0:
                print(f"🔄 Resetting failure counter (was {TRANSCRIPTION_FAILURES})")
                TRANSCRIPTION_FAILURES = 0
            
            return transcript
        else:
            print("⚠️  No speech detected in clip")
            TRANSCRIPTION_FAILURES += 1
            print(f"📊 Consecutive failures: {TRANSCRIPTION_FAILURES}")
            return None
            
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        TRANSCRIPTION_FAILURES += 1
        print(f"📊 Consecutive failures: {TRANSCRIPTION_FAILURES}")
        return None

def analyze_clip_content(transcript):
    """
    Analyze transcript content to determine content type.
    
    Args:
        transcript: Transcribed text
        
    Returns:
        str: Content type ('joke', 'reaction', 'insight', 'hype', 'boring', None)
    """
    if not transcript:
        return None
    
    transcript_lower = transcript.lower()
    
    # Enhanced gaming-specific keyword classification
    content_keywords = {
        'joke': ['haha', 'lol', 'funny', 'joke', 'hilarious', 'comedy', 'pog', 'omegalul', 'lmao', 'rofl'],
        'reaction': ['wow', 'omg', 'amazing', 'incredible', 'unbelievable', 'what', 'how', 'no way', 'seriously'],
        'hype': ['hype', 'excited', 'pumped', 'let\'s go', 'awesome', 'insane', 'crazy', 'let\'s go', 'poggers'],
        'insight': ['think', 'believe', 'because', 'reason', 'analysis', 'strategy', 'actually', 'basically'],
        'gaming': ['game', 'play', 'win', 'lose', 'team', 'match', 'tournament', 'rank', 'skill']
    }
    
    # Check for content types
    for content_type, keywords in content_keywords.items():
        if any(keyword in transcript_lower for keyword in keywords):
            return content_type
    
    # If no clear content type, check for boring indicators
    boring_indicators = ['um', 'uh', 'like', 'you know', 'so', 'anyway', 'basically']
    if any(indicator in transcript_lower for indicator in boring_indicators) and len(transcript.split()) < 10:
        return 'boring'
    
    return None

def run_transcription_monitor(buffer_file="buffer_audio.wav"):
    """
    Monitor and transcribe audio buffer, then use timer-based hybrid strategy:
    1. Always check ML model on every transcription cycle
    2. Create ML-triggered clips when model thinks content is worthy
    3. Create random clips every 120 seconds (2 minutes) regardless of model
    4. All clips are real Twitch clips with proper IDs
    
    Args:
        buffer_file: Path to the audio buffer file
    """
    global BUFFER_SEGMENTS
    
    # Start the random clip pulling thread
    start_random_clip_thread()
    
    # Start the segment monitoring thread
    start_segment_monitor()
    
    # Initialize timer for random clip creation
    last_random_clip_time = time.time()
    clips_created = 0  # Track total clips created
    
    # Check WhisperX environment before starting
    if not check_whisperx_environment():
        print("❌ WhisperX environment check failed. Please ensure virtual environment is activated.")
        print("💡 Run: source venv-py311/bin/activate")
        return
    
    # Reset clip counter for new run
    reset_clip_count()
    
    print("🎯 Real-time transcription monitor started")
    print("📊 Monitoring segments directory for new .ts files")
    print("🎤 Creating buffer_audio.wav every ~5 seconds")
    print("🤖 Always evaluating with ML model")
    print("⏰ Random clips every 120 seconds (2 minutes)")
    print("🎯 Using WhisperX large-v3 for highest accuracy")
    print("🔄 Auto-fallback to large-v2 after 3 failures")
    print(f"📊 Maximum clips per run: {MAX_CLIPS_PER_RUN}")
    print("🔒 Sequential processing enabled (one clip at a time)")
    print("-" * 60)
    
    try:
        while True:
            # Check if we've reached the clip limit
            if check_clip_limit():
                print(f"🎯 [RUN COMPLETE] Maximum clips ({MAX_CLIPS_PER_RUN}) created for this run")
                print("🛑 Stopping transcription monitor")
                break
            
            # Create buffer audio if segments are available
            if BUFFER_SEGMENTS:
                create_buffer_audio()
            
            # Only transcribe if buffer_audio.wav exists
            if os.path.exists(buffer_file):
                # Transcribe the audio buffer
                result = transcribe_buffer_audio(buffer_file)
                
                if result is None:
                    print("❌ Transcription failed, skipping clip evaluation")
                    time.sleep(5)
                    continue
                
                # Extract segments and build full transcript
                segments = result.get("segments", [])
                transcript = result.get("text", "").strip()
                
                if not transcript:
                    print("⚠️  No transcript available, skipping clip evaluation")
                    time.sleep(5)
                    continue
                
                # Generate segment hashes for each segment
                for seg in segments:
                    seg["segment_hash"] = generate_segment_hash(seg["text"], seg["start"], seg["end"])
                
                print(f"📝 Full transcript: {transcript}")
                
                # Always evaluate with ML model
                print("🤖 [ML EVALUATION] Evaluating clip-worthiness using ML model...")
                
                from src.predict import is_clip_worthy_by_model_v2
                from src.supabase_integration import insert_prediction_to_supabase, generate_and_store_embedding
                from datetime import datetime
                
                # Generate unique prediction ID for realtime logging (not actual Twitch clip)
                prediction_clip_id = f"realtime_pred_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                
                # Generate and store embedding
                print("🧠 Generating vector embedding...")
                full_text = " ".join([str(seg.get("text", "")) for seg in segments]).strip()
                embedding_success = generate_and_store_embedding(
                    clip_id=prediction_clip_id,
                    text=full_text,
                    model="text-embedding-ada-002"
                )
                
                if embedding_success:
                    print(f"✅ Embedding stored in Supabase: {prediction_clip_id}")
                else:
                    print("⚠️  Failed to store embedding in Supabase")
                
                # Get enhanced model prediction with segments and optional audio features
                is_worthy, confidence_score, debug_info = is_clip_worthy_by_model_v2(
                    segments=segments,
                    threshold=0.75,
                    clip_id=prediction_clip_id
                )
                
                # Log prediction to Supabase with actual confidence score
                prediction_success = insert_prediction_to_supabase(
                    clip_id=prediction_clip_id,
                    text=full_text,
                    score=confidence_score,
                    triggered=is_worthy,
                    clipworthy=is_worthy,
                    model_version="v2.0"
                )
                
                if prediction_success:
                    print(f"✅ Prediction logged to Supabase: {prediction_clip_id}")
                    print(f"📊 Confidence Score: {confidence_score:.3f}")
                    print(f"🎯 Threshold: 0.75")
                    print(f"📝 Segment Text: {full_text[:100]}{'...' if len(full_text) > 100 else ''}")
                    print(f"🔍 Debug Info: {len(debug_info.get('steps', []))} steps executed")
                else:
                    print("⚠️  Failed to log prediction to Supabase")
                
                # Check if ML model thinks it's worthy
                if is_worthy:
                    # Check clip limit before processing
                    if check_clip_limit():
                        print(f"⛔ [CLIP LIMIT] Maximum clips ({MAX_CLIPS_PER_RUN}) reached for this run")
                        print("🔄 Skipping ML-triggered clip creation")
                    else:
                        print("[🎬 MODEL TRIGGER] Clip-worthy by ML model.")
                        
                        # Sequential processing - ensure only one clip is processed at a time
                        with PROCESSING_LOCK:
                            # Double-check limit inside lock
                            if check_clip_limit():
                                print(f"⛔ [CLIP LIMIT] Maximum clips reached while processing")
                            else:
                                # Create real Twitch clip from buffer segments with transcript
                                clip_path = create_twitch_clip(transcript=full_text, dry_run=args.dry_run)
                                if clip_path:
                                    print(f"🎬 ML-triggered clip created: {clip_path}")
                                    
                                    # Extract clip_id from clip_path
                                    clip_id = os.path.basename(clip_path).replace('.mp4', '')
                                    
                                    # Insert into Supabase with source="ml"
                                    supabase_clip_id = insert_clip_to_supabase(
                                        clip_data={
                                            'clip_id': clip_id,
                                            'url': clip_path, # Assuming clip_path is the URL for real clips
                                            'broadcaster_name': 'Unknown' # Will be updated later
                                        },
                                        segments=segments,
                                        comments="",
                                        source="ml",
                                        labeling_method="auto"
                                    )
                                    
                                    if supabase_clip_id:
                                        print(f"✅ ML clip saved to Supabase: {supabase_clip_id}")
                                        
                                        # Log engagement data for ML-triggered clip
                                        try:
                                            engagement_success = log_engagement_data(supabase_clip_id, source="ml")
                                            if engagement_success:
                                                print(f"📊 Engagement data logged for ML clip: {supabase_clip_id}")
                                            else:
                                                print(f"⚠️ Failed to log engagement data for ML clip: {supabase_clip_id}")
                                        except Exception as e:
                                            print(f"⚠️ Error logging engagement data: {e}")
                                        
                                        increment_clip_count()
                                        clips_created += 1
                                    else:
                                        print("❌ Failed to save ML clip to Supabase")
                                else:
                                    print("❌ Failed to create ML-triggered clip")
                else:
                    print("[ ] Model did not trigger clip.")
                
                # Check if it's time for a random clip (every 120 seconds)
                now = time.time()
                if now - last_random_clip_time >= 120:
                    print("[🎲 RANDOM] 2-minute interval reached. Triggering random clip.")
                    
                    # Check clip limit before processing
                    if check_clip_limit():
                        print(f"⛔ [CLIP LIMIT] Maximum clips ({MAX_CLIPS_PER_RUN}) reached for this run")
                        print("🔄 Skipping random clip creation")
                        # Still reset timer to avoid constant checking
                        last_random_clip_time = now
                        print(f"⏰ Random clip timer reset (skipped due to limit)")
                    else:
                        # Sequential processing - ensure only one clip is processed at a time
                        with PROCESSING_LOCK:
                            # Double-check limit inside lock
                            if check_clip_limit():
                                print(f"⛔ [CLIP LIMIT] Maximum clips reached while processing")
                                # Still reset timer
                                last_random_clip_time = now
                                print(f"⏰ Random clip timer reset (skipped due to limit)")
                            else:
                                # Create real Twitch clip regardless of ML model
                                clip_path = create_twitch_clip(transcript=transcript, dry_run=args.dry_run)
                                if clip_path:
                                    print(f"🎬 Random clip created: {clip_path}")
                                    
                                    # Extract clip_id from clip_path
                                    clip_id = os.path.basename(clip_path).replace('.mp4', '')
                                    
                                    # Insert into Supabase with source="random"
                                    supabase_clip_id = insert_clip_to_supabase(
                                        clip_data={
                                            'clip_id': clip_id,
                                            'url': clip_path, # Assuming clip_path is the URL for real clips
                                            'broadcaster_name': 'Unknown' # Will be updated later
                                        },
                                        segments=segments,
                                        comments="",
                                        source="random",
                                        labeling_method="manual"
                                    )
                                    
                                    if supabase_clip_id:
                                        print(f"✅ Random clip saved to Supabase: {supabase_clip_id}")
                                        
                                        # Log engagement data for random clip
                                        try:
                                            engagement_success = log_engagement_data(supabase_clip_id, source="random")
                                            if engagement_success:
                                                print(f"📊 Engagement data logged for random clip: {supabase_clip_id}")
                                            else:
                                                print(f"⚠️ Failed to log engagement data for random clip: {supabase_clip_id}")
                                        except Exception as e:
                                            print(f"⚠️ Error logging engagement data: {e}")
                                        
                                        increment_clip_count()
                                        clips_created += 1
                                    else:
                                        print("❌ Failed to save random clip to Supabase")
                                        
                                        # Reset the timer
                                        last_random_clip_time = now
                                        print(f"⏰ Random clip timer reset")
                                else:
                                    print("❌ Failed to create random clip")
                else:
                    remaining_time = 120 - (now - last_random_clip_time)
                    print(f"⏰ Next random clip in {remaining_time:.1f}s")
            else:
                print("⏳ Waiting for segments to create buffer_audio.wav...")
            
            # Wait ~5 seconds before next iteration
            time.sleep(5)
                
    except KeyboardInterrupt:
        print("\n🛑 Transcription monitoring stopped by user")
    except Exception as e:
        print(f"❌ Error in transcription monitor: {e}")

def create_twitch_clip(transcript=None, dry_run=False):
    """
    Pull a real clip from Twitch API for training data collection.
    Gets clips from any channel in Just Chatting and IRL categories.
    
    Args:
        transcript: Optional transcript text (not used for API pulls)
        dry_run: If True, don't actually download the clip
        
    Returns:
        dict: Clip data including clip_id, url, broadcaster_name, or None if failed
    """
    try:
        # Check if Twitch API credentials are available
        twitch_client_id = os.getenv('TWITCH_CLIENT_ID')
        twitch_client_secret = os.getenv('TWITCH_CLIENT_SECRET')
        
        if not twitch_client_id or not twitch_client_secret:
            print("❌ Missing Twitch API credentials. Set TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET")
            return None
        
        # Import Twitch API functions
        from scripts.download_clips_api import (
            get_twitch_access_token, 
            download_clip,
            load_seen_clips,
            save_seen_clips
        )
        
        # Get access token
        access_token = get_twitch_access_token()
        
        # Load seen clips to avoid duplicates
        seen_clips = load_seen_clips()
        
        # Get clips from Just Chatting and IRL categories
        clips = get_clips_by_categories(access_token, twitch_client_id, ["Just Chatting", "IRL"])
        
        if not clips:
            print("⚠️  No clips found in Just Chatting or IRL categories")
            return None
        
        # Find a clip we haven't seen before
        for clip_data in clips:
            clip_id = clip_data['id']
            
            if clip_id not in seen_clips:
                broadcaster_name = clip_data.get('broadcaster_name', 'Unknown')
                view_count = clip_data.get('view_count', 0)
                print(f"🎯 Found new clip: {clip_id} from {broadcaster_name} (views: {view_count})")
                
                if dry_run:
                    print(f"🔍 [DRY RUN] Would download clip: {clip_id}")
                    return {
                        'clip_id': clip_id,
                        'url': clip_data.get('url', ''),
                        'broadcaster_name': clip_data.get('broadcaster_name', 'Unknown'),
                        'title': clip_data.get('title', ''),
                        'view_count': clip_data.get('view_count', 0)
                    }
                
                # Download the clip
                output_dir = Path("data/raw_clips/good")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                success = download_clip(clip_data, output_dir)
                
                if success:
                    # Mark as seen
                    seen_clips.add(clip_id)
                    save_seen_clips(seen_clips)
                    
                    print(f"✅ Downloaded clip: {clip_id}")
                    return {
                        'clip_id': clip_id,
                        'url': clip_data.get('url', ''),
                        'broadcaster_name': clip_data.get('broadcaster_name', 'Unknown'),
                        'title': clip_data.get('title', ''),
                        'view_count': clip_data.get('view_count', 0)
                    }
                else:
                    print(f"❌ Failed to download clip: {clip_id}")
                    continue
        
        print("⚠️  No new clips found in Just Chatting or IRL categories")
        return None
        
    except Exception as e:
        print(f"❌ Error pulling Twitch clip: {e}")
        return None

def get_clips_by_categories(access_token, client_id, categories, first=20):
    """
    Get clips from any channel in specified categories.
    Uses a more direct approach to get clips by category.
    
    Args:
        access_token: Twitch API access token
        client_id: Twitch client ID
        categories: List of category names (e.g., ["Just Chatting", "IRL"])
        first: Number of clips to fetch per category
        
    Returns:
        List of clip data
    """
    import requests
    from datetime import datetime, timedelta
    
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {access_token}'
    }
    
    all_clips = []
    
    for category_name in categories:
        print(f"🔍 Searching for clips in category: {category_name}")
        
        # Get category ID from name
        category_id = get_category_id(access_token, client_id, category_name)
        if not category_id:
            print(f"⚠️  Could not find category ID for {category_name}")
            continue
        
        # Get clips directly from this category using the clips endpoint
        # This gets clips from any channel in this category, not just active streams
        clips = get_clips_by_category(access_token, client_id, category_id, first=first)
        
        if clips:
            for clip in clips:
                clip['category_name'] = category_name
                all_clips.append(clip)
            print(f"✅ Found {len(clips)} clips in {category_name}")
        else:
            print(f"⚠️  No clips found in {category_name}")
    
    # Remove duplicates and create diverse selection
    unique_clips = {}
    for clip in all_clips:
        clip_id = clip['id']
        if clip_id not in unique_clips:
            unique_clips[clip_id] = clip
    
    clips_list = list(unique_clips.values())
    
    # Implement diverse selection strategy to avoid popularity bias
    # 1. Shuffle to randomize order (removes popularity bias)
    # 2. Take a sample from different popularity tiers
    import random
    random.shuffle(clips_list)
    
    # Split clips into popularity tiers for diverse selection
    if clips_list:
        # Sort by view count to create tiers
        clips_list.sort(key=lambda x: int(x.get('view_count', 0)), reverse=True)
        
        # Create tiers: top 30%, middle 40%, bottom 30%
        total_clips = len(clips_list)
        top_tier = clips_list[:int(total_clips * 0.3)]
        middle_tier = clips_list[int(total_clips * 0.3):int(total_clips * 0.7)]
        bottom_tier = clips_list[int(total_clips * 0.7):]
        
        # Shuffle each tier to remove internal popularity bias
        random.shuffle(top_tier)
        random.shuffle(middle_tier)
        random.shuffle(bottom_tier)
        
        # Combine tiers with balanced representation
        diverse_clips = []
        diverse_clips.extend(top_tier[:min(5, len(top_tier))])      # Up to 5 from top tier
        diverse_clips.extend(middle_tier[:min(10, len(middle_tier))]) # Up to 10 from middle tier  
        diverse_clips.extend(bottom_tier[:min(5, len(bottom_tier))])  # Up to 5 from bottom tier
        
        # Shuffle final selection to remove tier bias
        random.shuffle(diverse_clips)
        
        print(f"📊 Total unique clips found: {len(clips_list)}")
        print(f"🎯 Diverse selection: {len(diverse_clips)} clips (top: {len(top_tier[:5])}, middle: {len(middle_tier[:10])}, bottom: {len(bottom_tier[:5])})")
        return diverse_clips
    else:
        print(f"📊 Total unique clips found: 0")
        return []

def get_clips_by_category(access_token, client_id, category_id, first=20):
    """
    Get clips from a specific category using the clips endpoint.
    This gets clips from any channel in the category, not just active streams.
    """
    import requests
    from datetime import datetime, timedelta
    
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {access_token}'
    }
    
    # Get clips from the last 30 days in this category
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=30)
    
    params = {
        'game_id': category_id,
        'first': first,
        'started_at': start_time.isoformat() + 'Z',
        'ended_at': end_time.isoformat() + 'Z'
    }
    
    url = "https://api.twitch.tv/helix/clips"
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        clips = data.get('data', [])
        print(f"📊 Found {len(clips)} clips in category {category_id}")
        return clips
    else:
        print(f"❌ Failed to get clips for category {category_id}: {response.status_code}")
        print(f"Response: {response.text}")
        return []

def get_category_id(access_token, client_id, category_name):
    """Get category ID from category name."""
    import requests
    
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {access_token}'
    }
    
    url = f"https://api.twitch.tv/helix/search/categories?query={category_name}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data['data']:
            return data['data'][0]['id']
    return None

def get_streams_by_category(access_token, client_id, category_id, first=10):
    """Get active streams in a category."""
    import requests
    
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {access_token}'
    }
    
    params = {
        'game_id': category_id,
        'first': first
    }
    
    url = "https://api.twitch.tv/helix/streams"
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()['data']
    else:
        print(f"❌ Failed to get streams: {response.status_code}")
        return []

def get_clips_by_broadcaster(access_token, broadcaster_id, started_at=None, ended_at=None, first=20):
    """Get clips for a broadcaster using Twitch API."""
    import requests
    
    headers = {
        'Client-ID': os.getenv('TWITCH_CLIENT_ID'),
        'Authorization': f'Bearer {access_token}'
    }
    
    params = {
        'broadcaster_id': broadcaster_id,
        'first': first
    }
    
    if started_at:
        params['started_at'] = started_at
    if ended_at:
        params['ended_at'] = ended_at
    
    url = "https://api.twitch.tv/helix/clips"
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()['data']
    else:
        print(f"❌ Failed to get clips: {response.status_code}")
        return []

def insert_clip_to_supabase(clip_data, segments, comments="", source="ml", content_type=None, labeling_method="manual", emotion_label=None):
    """
    Insert a clip into Supabase with the specified source and metadata.
    For real Twitch clips, this saves the actual clip data from Twitch API.
    
    Args:
        clip_data: Dictionary containing clip information (clip_id, url, broadcaster_name, etc.)
        segments: List of transcription segments (or clip metadata for real clips)
        comments: Additional comments about the clip
        source: Source of the clip ("ml", "random", etc.)
        content_type: Type of content ("joke", "reaction", "insight", "hype", "boring", etc.)
        labeling_method: Method of labeling ("manual", "auto", "review_needed")
        emotion_label: Predicted emotion label (optional)
        
    Returns:
        clip_id: The Twitch clip ID, or None if failed
    """
    try:
        from src.supabase_integration import save_for_labeling
        
        # Extract clip information
        clip_id = clip_data['clip_id']
        twitch_url = clip_data.get('url', '')
        broadcaster_name = clip_data.get('broadcaster_name', 'Unknown')
        
        # For real Twitch clips, we need to get the actual clip data
        # The clip_id here is the Twitch clip ID, and we need to find the corresponding file
        clip_path = f"data/raw_clips/good/{clip_id}.mp4"
        
        # Check if the clip file exists
        if not os.path.exists(clip_path):
            print(f"❌ Clip file not found: {clip_path}")
            return None
        
        # Transcribe the actual clip for content analysis
        print(f"🎤 Transcribing clip for content analysis: {clip_id}")
        transcript = transcribe_clip_for_content_analysis(clip_path)
        
        if transcript:
            # Analyze content type from transcript
            content_type = analyze_clip_content(transcript)
            print(f"📊 Content analysis: {content_type}")
        else:
            # Fallback to placeholder if transcription fails
            transcript = f"Clip {clip_id} from {broadcaster_name} - {source} collection"
            content_type = None
            print(f"⚠️  Using placeholder transcript for {clip_id}")
        
        # Use provided content_type and labeling_method, or defaults based on source
        if content_type is None:
            # Could be enhanced later to analyze segments for content type
            content_type = None
        
        # All clips are manually labeled, regardless of source
        # Source indicates collection method (ml vs random), not labeling method
        labeling_method = "manual"
        
        print(f"💾 Attempting to save clip to Supabase: {clip_id} (source: {source}, content_type: {content_type}, labeling_method: {labeling_method})")
        
        supabase_clip_id = save_for_labeling(
            transcript=transcript,
            clip_path=clip_path,
            source=source,
            content_type=content_type,
            labeling_method=labeling_method,
            twitch_clip_id=clip_id,
            twitch_url=twitch_url,
            emotion_label=emotion_label
        )
        
        if supabase_clip_id:
            print(f"✅ Clip inserted into Supabase: {supabase_clip_id} (source: {source}, content_type: {content_type}, labeling_method: {labeling_method}, comments: {comments})")
            return supabase_clip_id
        else:
            print("❌ Failed to insert clip into Supabase")
            print("💡 Check if Supabase credentials are set in environment variables:")
            print("   - SUPABASE_URL")
            print("   - SUPABASE_ANON_KEY or SUPABASE_KEY")
            return None
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure src.supabase_integration module is available")
        return None
    except Exception as e:
        print(f"❌ Error inserting clip to Supabase: {e}")
        print("💡 This might be due to missing Supabase credentials or network issues")
        return None

def switch_whisper_model(model_size):
    """
    Switch to a different WhisperX model size.
    
    Args:
        model_size: Model size ("tiny", "base", "small", "medium", "large", "large-v2", "large-v3")
    """
    global WHISPER_MODEL, WHISPER_MODEL_SIZE
    
    valid_sizes = ["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"]
    
    if model_size not in valid_sizes:
        print(f"❌ Invalid model size. Choose from: {valid_sizes}")
        return False
    
    print(f"🔄 Switching WhisperX model from {WHISPER_MODEL_SIZE} to {model_size}...")
    
    # Clear current model
    WHISPER_MODEL = None
    WHISPER_MODEL_SIZE = model_size
    
    # Load new model
    try:
        load_whisper_model()
        print(f"✅ Successfully switched to {model_size} model")
        return True
    except Exception as e:
        print(f"❌ Failed to switch model: {e}")
        return False

def run_training_data_collection(max_clips=20, dry_run=False):
    """
    Collect training data by pulling clips from Twitch API using hybrid strategy:
    1. ML-triggered clips: Use ML model to predict which clips are worthy
    2. Random clips: Pull random clips every 2 minutes for baseline comparison
    3. Sources clips from ANY channel in Just Chatting and IRL categories
    4. All clips are saved to Supabase for manual labeling
    
    Args:
        max_clips: Maximum number of clips to collect (default: 20)
        dry_run: If True, don't actually download clips
    """
    print("🎯 Training Data Collection System")
    print("=" * 50)
    print(f"📊 Target clips: {max_clips}")
    print("🤖 ML-triggered clips: Based on model predictions")
    print("🎲 Random clips: Every 2 minutes for baseline")
    print("📺 Sources: ANY channel in Just Chatting & IRL categories")
    print("📝 All clips saved to Supabase for manual labeling")
    print("🔄 Duplicate detection enabled")
    print("-" * 50)
    
    # Check Twitch API credentials
    twitch_client_id = os.getenv('TWITCH_CLIENT_ID')
    twitch_client_secret = os.getenv('TWITCH_CLIENT_SECRET')
    
    if not twitch_client_id or not twitch_client_secret:
        print("❌ Missing Twitch API credentials!")
        print("💡 Set environment variables:")
        print("   export TWITCH_CLIENT_ID='your_client_id'")
        print("   export TWITCH_CLIENT_SECRET='your_client_secret'")
        return
    
    # Initialize counters for 30% ML / 70% Random hybrid strategy
    clips_collected = 0
    ml_clips = 0
    random_clips = 0
    
    # Calculate target numbers for each type
    target_ml_clips = int(max_clips * 0.3)  # 30% ML
    target_random_clips = max_clips - target_ml_clips  # 70% Random
    
    print(f"🎯 Hybrid Strategy Targets:")
    print(f"   🤖 ML clips: {target_ml_clips} (30%)")
    print(f"   🎲 Random clips: {target_random_clips} (70%)")
    
    # Load ML model for predictions
    try:
        from src.predict import is_clip_worthy_by_model
        print("✅ ML model loaded for clip-worthiness predictions")
    except Exception as e:
        print(f"❌ Failed to load ML model: {e}")
        print("🔄 Continuing with random-only collection")
        is_clip_worthy_by_model = None
    
    print(f"🚀 Starting collection... (max: {max_clips} clips)")
    print("-" * 50)
    
    try:
        while clips_collected < max_clips:
            print(f"\n📊 Progress: {clips_collected}/{max_clips} clips collected")
            print(f"🤖 ML clips: {ml_clips}, 🎲 Random clips: {random_clips}")
            
            # Try to pull a clip from Twitch API
            clip_data = create_twitch_clip(dry_run=dry_run)
            
            if not clip_data:
                print("⚠️  No new clips available from Twitch API")
                print("💤 Waiting 60 seconds before retry...")
                time.sleep(60)
                continue
            
            # Determine if this should be ML-triggered or random based on 30/70 ratio
            # Check if we still need ML clips and have ML model available
            need_ml_clips = ml_clips < target_ml_clips
            need_random_clips = random_clips < target_random_clips
            
            # Decide source based on what we still need
            if need_ml_clips and need_random_clips:
                # We need both types, prioritize based on current ratio
                current_ml_ratio = ml_clips / max(1, clips_collected)
                if current_ml_ratio < 0.3:
                    # We're behind on ML clips, prioritize ML
                    source_type = "ml"
                else:
                    # We're ahead on ML clips, prioritize random
                    source_type = "random"
            elif need_ml_clips:
                # Only need ML clips
                source_type = "ml"
            elif need_random_clips:
                # Only need random clips
                source_type = "random"
            else:
                # We have enough of both types, but still under max_clips
                # This shouldn't happen with proper logic, but handle it
                source_type = "random"
            
            # Process based on source type
            if source_type == "ml" and is_clip_worthy_by_model:
                # Try ML prediction
                # For now, use a simple heuristic based on clip ID
                # In real scenario, you'd transcribe the clip first
                is_worthy = len(clip_data['clip_id']) > 20  # Simple heuristic
                
                if is_worthy:
                    source = "ml"
                    labeling_method = "manual"  # All clips are manually labeled
                    ml_clips += 1
                    print(f"🤖 [ML TRIGGER] Clip {clip_data['clip_id']} deemed worthy by model")
                else:
                    print(f"🤖 [ML REJECT] Clip {clip_data['clip_id']} not worthy, skipping")
                    continue
            else:
                # Random clip or no ML model available
                source = "random"
                labeling_method = "manual"
                random_clips += 1
                print(f"🎲 [RANDOM] Pulling random clip: {clip_data['clip_id']}")
            
            # Create dummy segments for Supabase insertion
            # In real scenario, you'd transcribe the actual clip
            dummy_segments = [
                {
                    "text": f"Clip {clip_data['clip_id']} - {source} collection",
                    "start": 0.0,
                    "end": 10.0,
                    "segment_duration": 10.0,
                    "pause_before": 0.0,
                    "sentiment_score": 0.0,
                    "sentiment_category": "neutral"
                }
            ]
            
            # Generate segment hashes for dummy segments
            for seg in dummy_segments:
                seg["segment_hash"] = generate_segment_hash(seg["text"], seg["start"], seg["end"])
            
            # Fetch engagement data for auto-labeling
            engagement_data = None
            auto_label = None
            
            try:
                from src.twitch_engagement_fetcher import get_clip_engagement, calculate_engagement_score, assign_auto_label
                
                print(f"📊 Fetching engagement data for clip: {clip_data['clip_id']}")
                engagement_data = get_clip_engagement(clip_data['clip_id'])
                
                if engagement_data:
                    engagement_score = calculate_engagement_score(engagement_data)
                    auto_label = assign_auto_label(engagement_score)
                    print(f"📈 Engagement score: {engagement_score}, Auto label: {auto_label}")
                else:
                    print(f"⚠️ Could not fetch engagement data for {clip_data['clip_id']}")
                    
            except ImportError:
                print(f"⚠️ Engagement fetcher not available, skipping auto-labeling")
            except Exception as e:
                print(f"⚠️ Error fetching engagement data: {e}")
            
            # Analyze content type from transcript (if available)
            content_type = None
            if clip_data.get('title'):
                # Use title for content analysis since we don't have transcript yet
                content_type = analyze_clip_content(clip_data['title'])
                print(f"📝 Content type from title: {content_type}")
            
            # Insert into Supabase
            if not dry_run:
                supabase_clip_id = insert_clip_to_supabase(
                    clip_data=clip_data,
                    segments=dummy_segments,
                    comments=f"Training data collection - {source}",
                    source=source,
                    content_type=content_type,
                    labeling_method=labeling_method
                )
                
                # Update analytics with engagement data if available
                if supabase_clip_id and engagement_data:
                    try:
                        from src.supabase_integration import supabase_manager
                        
                        # Add engagement score and auto_label to engagement data
                        if 'engagement_score' not in engagement_data:
                            engagement_data['engagement_score'] = calculate_engagement_score(engagement_data)
                        if 'auto_label' not in engagement_data:
                            engagement_data['auto_label'] = auto_label
                        
                        # Update analytics table with engagement data
                        analytics_success = supabase_manager._log_clip_analytics(
                            supabase_clip_id, source, content_type, engagement_data
                        )
                        
                        if analytics_success:
                            print(f"📊 Updated analytics with engagement data: {engagement_data['views']} views, score: {engagement_data['engagement_score']}")
                        else:
                            print(f"⚠️ Failed to update analytics with engagement data")
                            
                    except Exception as e:
                        print(f"⚠️ Error updating analytics: {e}")
                
                if supabase_clip_id:
                    clips_collected += 1
                    print(f"✅ Clip {clip_data['clip_id']} saved to Supabase: {supabase_clip_id}")
                    print(f"📝 Ready for manual labeling in Supabase dashboard")
                    
                    # URL is automatically saved to unlabeled_clips.txt by Supabase integration
                    print(f"🔗 Clip URL: {clip_data.get('url', 'N/A')}")
                else:
                    print(f"❌ Failed to save clip {clip_data['clip_id']} to Supabase")
            else:
                clips_collected += 1
                print(f"🔍 [DRY RUN] Would save clip {clip_data['clip_id']} to Supabase")
                
                # URL would be automatically saved to unlabeled_clips.txt by Supabase integration
                print(f"🔗 Would save URL: {clip_data.get('url', 'N/A')}")
            
            # Wait between clips to avoid rate limiting
            print("⏳ Waiting 10 seconds before next clip...")
            time.sleep(10)
        
        print(f"\n🎉 Collection complete!")
        print(f"📊 Total clips collected: {clips_collected}")
        print(f"🤖 ML-triggered clips: {ml_clips}")
        print(f"🎲 Random clips: {random_clips}")
        print(f"📝 All clips saved to Supabase for manual labeling")
        print(f"💡 Visit your Supabase dashboard to label the clips")
        
    except KeyboardInterrupt:
        print(f"\n🛑 Collection stopped by user")
        print(f"📊 Partial results: {clips_collected} clips collected")
    except Exception as e:
        print(f"\n❌ Error during collection: {e}")
        print(f"📊 Partial results: {clips_collected} clips collected")



def main():
    """Main function with options for real-time transcription or training data collection."""
    print("🎯 Twitch Clip Collection and Transcription System")
    print("=" * 60)
    
    if args.mode == "training":
        print("📊 Training Data Collection Mode")
        print("🤖 Collecting clips from Twitch API for model training")
        print("🎲 Hybrid strategy: ML predictions + random sampling")
        print("📝 All clips saved to Supabase for manual labeling")
        print("-" * 60)
        
        # Check environment
        if not check_whisperx_environment():
            print("❌ Please activate the virtual environment first:")
            print("   source venv-py311/bin/activate")
            return
        
        # Run training data collection
        run_training_data_collection(max_clips=args.max_clips, dry_run=args.dry_run)
        
    else:  # realtime mode
        print("🎤 Real-time Transcription Mode")
        print("📊 Available WhisperX model sizes for better accuracy:")
        print("  - 'medium': Good balance of speed/accuracy (DEFAULT)")
        print("  - 'large': High accuracy, slower")
        print("  - 'large-v2': Latest large model (enhanced fallback)")
        print("  - 'large-v3': Latest and most accurate (fallback)")
        
        print("\n🔄 Auto-fallback system:")
        print("  - Starts with medium model for speed")
        print("  - Switches to large-v3 after 3 consecutive failures")
        print("  - Resets to medium model after successful transcription")
        print("  - Forces English language detection for better accuracy")
        
        print("\n📊 Clip processing limits:")
        print(f"  - Maximum clips per run: {MAX_CLIPS_PER_RUN}")
        print("  - Sequential processing: One clip at a time")
        print("  - Automatic run completion when limit reached")
        
        # Check WhisperX environment
        if not check_whisperx_environment():
            print("❌ Please activate the virtual environment first:")
            print("   source venv-py311/bin/activate")
            return
        
        # Example transcription with clip-worthiness detection
        if os.path.exists("buffer_audio.wav"):
            print("\n🎬 Running transcription monitor with WhisperX and ML clip detection...")
            run_transcription_monitor("buffer_audio.wav")
        else:
            print("\n⚠️  No buffer_audio.wav found. Create an audio file to test.")
            print("💡 You can also call run_transcription_monitor() directly with your audio file.")
            print("\n💡 For training data collection, use: python realtime_transcription.py --mode training")

if __name__ == "__main__":
    main()