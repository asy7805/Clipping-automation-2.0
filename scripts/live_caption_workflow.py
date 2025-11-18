#!/usr/bin/env python3
"""
Live streaming with real-time caption workflow.
Captures stream in short segments and adds captions as they're created.
"""

import os
import sys
import subprocess
import time
import whisperx
import torch
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from preedit_and_post import transcribe_video, create_srt_file, burn_captions


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


def capture_with_realtime_captions(channel: str, segment_duration: int = 30, max_segments: int = 10):
    """
    Capture stream in segments and add captions in near real-time.
    
    Args:
        channel: Twitch channel name
        segment_duration: Duration of each segment in seconds
        max_segments: Maximum number of segments to process
    """
    # Ensure FFmpeg is in PATH
    ffmpeg_dir = os.path.dirname(get_ffmpeg_path())
    os.environ["PATH"] += f";{ffmpeg_dir}"
    
    print("=" * 60)
    print("🎬 Real-Time Caption Workflow")
    print("=" * 60)
    print(f"📺 Channel: {channel}")
    print(f"⏱️  Segment duration: {segment_duration}s")
    print(f"📊 Max segments: {max_segments}")
    print("=" * 60 + "\n")
    
    captioned_segments = []
    
    for i in range(max_segments):
        timestamp = int(time.time())
        segment_file = f"segment_{i:03d}_{timestamp}.mp4"
        
        print(f"\n[{i+1}/{max_segments}] Capturing segment...")
        
        # Capture segment
        try:
            cmd = [
                "streamlink",
                f"https://www.twitch.tv/{channel}",
                "best",
                "--hls-live-restart",
                "-o", segment_file
            ]
            
            process = subprocess.Popen(cmd)
            time.sleep(segment_duration + 5)  # Add buffer
            process.terminate()
            process.wait(timeout=5)
            
            if not Path(segment_file).exists():
                print(f"❌ Segment {i+1} failed to capture")
                continue
                
            print(f"✅ Captured: {segment_file}")
            
            # Add captions to segment
            print(f"📝 Adding captions to segment {i+1}...")
            captioned_file = segment_file.replace('.mp4', '_captioned.mp4')
            
            # Use the preedit_and_post script to add captions
            transcribe_cmd = [
                sys.executable,
                "scripts/preedit_and_post.py",
                "--input", segment_file,
                "--output", captioned_file,
                "--model", "tiny",  # Fast model for real-time
                "--style", "modern"
            ]
            
            result = subprocess.run(transcribe_cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and Path(captioned_file).exists():
                print(f"✅ Captioned: {captioned_file}")
                captioned_segments.append(captioned_file)
            else:
                print(f"⚠️  Captioning failed, using original: {result.stderr[:200]}")
                captioned_segments.append(segment_file)
            
        except Exception as e:
            print(f"❌ Error in segment {i+1}: {e}")
            break
    
    # Concatenate all segments
    if captioned_segments:
        print("\n🔗 Concatenating segments...")
        final_output = f"{channel}_realtime_captioned_{int(time.time())}.mp4"
        
        ffmpeg = get_ffmpeg_path()
        
        # Create file list for ffmpeg concat
        file_list = Path("file_list.txt")
        with open(file_list, 'w') as f:
            for seg in captioned_segments:
                f.write(f"file '{seg}'\n")
        
        # Concatenate
        cmd = [
            ffmpeg,
            "-f", "concat",
            "-safe", "0",
            "-i", str(file_list),
            "-c", "copy",
            "-y",
            final_output
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"\n✅ Final output: {final_output}")
            print(f"📊 Total segments: {len(captioned_segments)}")
            print(f"⏱️  Total duration: ~{segment_duration * len(captioned_segments)}s")
        
        # Clean up
        file_list.unlink()
    
    return final_output if captioned_segments else None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Real-time caption workflow")
    parser.add_argument("channel", nargs="?", default="tenz", help="Twitch channel")
    parser.add_argument("--duration", type=int, default=30, help="Segment duration in seconds")
    parser.add_argument("--max", type=int, default=5, help="Max segments")
    
    args = parser.parse_args()
    
    capture_with_realtime_captions(args.channel, args.duration, args.max)

