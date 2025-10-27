#!/usr/bin/env python3
"""
Ultra-fast real-time captions with multi-threaded processing.
Captures audio every 5 seconds and transcribes in parallel for fast updates.
"""

import os
import sys
import subprocess
import threading
import time
import whisperx
import torch
from pathlib import Path
from collections import deque
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_ffmpeg_path():
    winget = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin\ffmpeg.exe"
    )
    if os.path.exists(winget):
        return winget
    bundled = Path(__file__).parent.parent / "tools" / "ffmpeg-master-latest-win64-gpl" / "bin" / "ffmpeg.exe"
    if bundled.exists():
        return str(bundled)
    return "ffmpeg"


class UltraFastCaptioner:
    """Fast captioner with parallel processing."""
    
    def __init__(self):
        print("📥 Loading WhisperX (tiny, int8)...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisperx.load_model("tiny", device, compute_type="int8")
        self.model_lock = threading.Lock()
        self.captions = deque(maxlen=10)  # Keep last 10 captions
        print(f"✅ Ready on {device}")
    
    def transcribe_chunk(self, audio_path: str, timestamp: float):
        """Transcribe an audio chunk."""
        start = time.time()
        
        try:
            with self.model_lock:
                result = self.model.transcribe(audio_path, language="en")
            
            elapsed = time.time() - start
            text = result.get("text", "").strip()
            
            if text:
                self.captions.append({
                    "text": text[:100],
                    "timestamp": timestamp,
                    "process_time": elapsed
                })
                print(f"[{elapsed:.1f}s] {text[:60]}...")
            
            return text
        except Exception as e:
            print(f"⚠️  Error: {e}")
            return ""
    
    def process_stream(self, channel: str, duration: int = 60):
        """Process stream with fast captioning."""
        print(f"🎬 Starting {duration}s capture from {channel}")
        print("⚡ Processing every 5 seconds with parallel transcription")
        print("=" * 60 + "\n")
        
        output_file = f"{channel}_ultra_realtime_{int(time.time())}.mp4"
        
        # Capture with streamlink
        capture_proc = subprocess.Popen(
            ["streamlink", f"https://twitch.tv/{channel}", "best", "-o", "temp_capture.mp4"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        
        ffmpeg = get_ffmpeg_path()
        audio_chunks = []
        
        start = time.time()
        while (time.time() - start) < duration:
            current_time = time.time() - start
            
            # Extract 5-second audio chunk
            audio_file = f"chunk_{len(audio_chunks)}.wav"
            
            cmd = [
                ffmpeg, "-y", "-ss", str(max(0, current_time-5)),
                "-t", "5",
                "-i", "temp_capture.mp4",
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                "-loglevel", "error",
                audio_file
            ]
            
            try:
                subprocess.run(cmd, capture_output=True, timeout=6)
                if Path(audio_file).exists():
                    audio_chunks.append((audio_file, current_time))
            except:
                pass
            
            # Process in separate thread
            if audio_chunks:
                chunk, ts = audio_chunks.pop(0)
                threading.Thread(
                    target=self.transcribe_chunk,
                    args=(chunk, ts),
                    daemon=True
                ).start()
            
            time.sleep(5)
        
        # Wait for final captions
        print("\n⏳ Waiting for final transcriptions...")
        time.sleep(15)
        
        capture_proc.terminate()
        
        # Create SRT from captions
        print("\n📝 Creating SRT file...")
        srt_file = output_file.replace(".mp4", ".srt")
        with open(srt_file, 'w') as f:
            for i, cap in enumerate(self.captions, 1):
                start_ts = cap['timestamp']
                end_ts = start_ts + 5
                f.write(f"{i}\n")
                f.write(f"{self.format_time(start_ts)} --> {self.format_time(end_ts)}\n")
                f.write(f"{cap['text']}\n\n")
        
        print(f"✅ SRT saved: {srt_file}")
        print(f"📊 Total captions: {len(self.captions)}")
        
        return srt_file
    
    def format_time(self, seconds):
        """Format seconds to SRT time format."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("channel", nargs="?", default="tenz")
    parser.add_argument("--duration", type=int, default=60)
    
    args = parser.parse_args()
    
    # Add FFmpeg to PATH
    os.environ["PATH"] += f";{os.path.dirname(get_ffmpeg_path())}"
    
    captioner = UltraFastCaptioner()
    srt = captioner.process_stream(args.channel, args.duration)
    
    print(f"\n✅ Complete! SRT file: {srt}")

