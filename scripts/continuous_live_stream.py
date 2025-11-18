#!/usr/bin/env python3
"""
Continuous live stream capture with periodic captioning.
Captures stream continuously and adds captions to segments as they're created.
"""

import os
import sys
import subprocess
import time
import threading
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

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


def continuous_capture_with_captions(channel: str, segment_duration: int = 60):
    """
    Continuously capture stream and add captions to each segment.
    
    Args:
        channel: Twitch channel name
        segment_duration: Duration of each segment in seconds
    """
    os.environ["PATH"] += f";{os.path.dirname(get_ffmpeg_path())}"
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1wY3Zna25mamN4c2FsYnR4YWJrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MzMzNjUwNywiZXhwIjoyMDY4OTEyNTA3fQ.XpufYrZCWddh2XKodabO201LAiuaTocx8lAD6JSctYE"
    
    print("=" * 60)
    print("🎬 CONTINUOUS LIVE STREAM CAPTURE")
    print("=" * 60)
    print(f"📺 Channel: {channel}")
    print(f"⏱️  Segment duration: {segment_duration}s")
    print(f"🔄 Capturing continuously...")
    print("🛑 Press Ctrl+C to stop")
    print("=" * 60 + "\n")
    
    segment_num = 0
    
    try:
        while True:
            segment_num += 1
            timestamp = int(time.time())
            segment_file = f"live_segment_{segment_num:04d}_{timestamp}.mp4"
            
            print(f"\n[{segment_num}] Capturing {segment_duration}s segment...")
            
            # Capture segment
            try:
                cmd = [
                    "streamlink",
                    f"https://twitch.tv/{channel}",
                    "best",
                    "--hls-live-restart",
                    "-o", segment_file
                ]
                
                process = subprocess.Popen(cmd)
                time.sleep(segment_duration)
                process.terminate()
                process.wait(timeout=5)
                
                if not Path(segment_file).exists():
                    print(f"❌ Segment {segment_num} failed")
                    continue
                
                file_size = Path(segment_file).stat().st_size / 1024 / 1024
                print(f"✅ Captured: {segment_file} ({file_size:.1f} MB)")
                
                # Process captions in background thread
                def process_captions():
                    try:
                        captioned_file = segment_file.replace('.mp4', '_captioned.mp4')
                        
                        print(f"📝 Adding captions to segment {segment_num}...")
                        
                        caption_cmd = [
                            sys.executable,
                            "scripts/preedit_and_post.py",
                            "--input", segment_file,
                            "--output", captioned_file,
                            "--model", "tiny",
                            "--style", "modern"
                        ]
                        
                        result = subprocess.run(caption_cmd, capture_output=True, text=True)
                        
                        if result.returncode == 0 and Path(captioned_file).exists():
                            print(f"✅ Captioned: {captioned_file}")
                            
                            # Upload to Supabase
                            try:
                                upload_cmd = [sys.executable, "scripts/upload_captioned_clip.py", captioned_file]
                                subprocess.run(upload_cmd, capture_output=True)
                                print(f"☁️  Uploaded to Supabase")
                            except:
                                pass
                        else:
                            print(f"⚠️  Captioning failed")
                    except Exception as e:
                        print(f"❌ Processing error: {e}")
                
                # Process in background
                threading.Thread(target=process_captions, daemon=True).start()
                
            except Exception as e:
                print(f"❌ Error in segment {segment_num}: {e}")
                time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping continuous capture...")
        print(f"📊 Total segments captured: {segment_num}")
        print("✅ Complete!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Continuous live stream capture")
    parser.add_argument("channel", nargs="?", default="tenz", help="Twitch channel")
    parser.add_argument("--duration", type=int, default=60, help="Segment duration (seconds)")
    
    args = parser.parse_args()
    
    continuous_capture_with_captions(args.channel, args.duration)

