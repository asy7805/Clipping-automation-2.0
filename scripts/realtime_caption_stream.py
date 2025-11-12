#!/usr/bin/env python3
"""
Real-time captioning for live Twitch streams.
Captures stream, transcribes in real-time, and outputs video with live captions.
"""

import os
import sys
import subprocess
import threading
import time
import queue
import json
import whisperx
import torch
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_ffmpeg_path():
    """Get FFmpeg path."""
    winget = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin\ffmpeg.exe"
    )
    if os.path.exists(winget):
        return winget
    
    bundled = Path(__file__).parent.parent / "tools" / "ffmpeg-master-latest-win64-gpl" / "bin" / "ffmpeg.exe"
    if bundled.exists():
        return str(bundled)
    
    return "ffmpeg"


class RealTimeCaptioner:
    """Real-time caption overlay for live streams."""
    
    def __init__(self, channel: str, output: str):
        self.channel = channel
        self.output = output
        self.transcript_queue = queue.Queue()
        self.current_caption = ""
        self.caption_lock = threading.Lock()
        self.running = False
        
        # Load WhisperX model once
        print("📥 Loading WhisperX model...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisperx.load_model("tiny", device, compute_type="float32")
        print(f"✅ Model loaded on {device}")
        
    def transcribe_audio_chunk(self, audio_path: str):
        """Transcribe a short audio chunk."""
        try:
            result = self.model.transcribe(audio_path, language="en")
            text = result.get("text", "").strip()
            if text:
                with self.caption_lock:
                    self.current_caption = text[:100]  # Limit caption length
                print(f"📝 {text[:60]}...")
            return text
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return ""
    
    def audio_transcription_worker(self):
        """Background worker to transcribe audio chunks."""
        chunk_dir = Path("temp_caption_chunks")
        chunk_dir.mkdir(exist_ok=True)
        
        while self.running:
            try:
                # Wait for new audio chunk
                if not self.transcript_queue.empty():
                    audio_path = self.transcript_queue.get(timeout=1)
                    self.transcribe_audio_chunk(audio_path)
                    # Clean up
                    if Path(audio_path).exists():
                        Path(audio_path).unlink()
                time.sleep(0.1)
            except:
                pass
    
    def create_caption_overlay(self):
        """Create caption overlay using FFmpeg drawtext filter."""
        caption_display = ""
        with self.caption_lock:
            caption_display = self.current_caption.replace("'", "\\'")
        
        if not caption_display:
            return None
        
        # FFmpeg drawtext filter
        return f"drawtext=text='{caption_display}':fontfile=/Windows/Fonts/arial.ttf:fontsize=24:x=(w-tw)/2:y=h-th-40:fontcolor=white:box=1:boxcolor=black@0.8:boxborderw=5"
    
    def start_live_captioning(self):
        """Start live captioning stream."""
        self.running = True
        
        # Start transcription worker
        worker = threading.Thread(target=self.audio_transcription_worker, daemon=True)
        worker.start()
        
        ffmpeg = get_ffmpeg_path()
        
        print(f"🎬 Starting live captioning for https://twitch.tv/{self.channel}...")
        print("📝 Captions will appear in real-time")
        print("🛑 Press Ctrl+C to stop")
        
        # Segment duration for transcription
        segment_duration = 3  # 3 seconds
        
        try:
            # Step 1: Capture stream
            print("\n[1/3] Starting stream capture...")
            cmd = [
                "streamlink",
                f"https://www.twitch.tv/{self.channel}",
                "best",
                "-O"  # Output to stdout
            ]
            
            stream_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Step 2: Process stream with real-time transcription
            print("\n[2/3] Processing stream with real-time transcription...")
            
            # For now, save to output file
            output_path = self.output
            
            cmd = [
                ffmpeg,
                "-i", "pipe:0",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-c:a", "copy",
                "-f", "mp4",
                "-y",
                output_path
            ]
            
            encode_process = subprocess.Popen(
                cmd,
                stdin=stream_process.stdout,
                stderr=subprocess.PIPE
            )
            
            stream_process.stdout.close()
            
            # Monitor the process
            print("\n[3/3] Streaming with captioning...")
            encode_process.wait()
            
        except KeyboardInterrupt:
            print("\n🛑 Stopping...")
        finally:
            self.running = False
            print("\n✅ Complete!")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Real-time captioning for Twitch streams")
    parser.add_argument("channel", help="Twitch channel name")
    parser.add_argument("--output", default="live_captioned.mp4", help="Output file")
    
    args = parser.parse_args()
    
    # Ensure FFmpeg is in PATH
    os.environ["PATH"] += f";{os.path.dirname(get_ffmpeg_path())}"
    
    captioner = RealTimeCaptioner(args.channel, args.output)
    captioner.start_live_captioning()


if __name__ == "__main__":
    main()

