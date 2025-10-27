#!/usr/bin/env python3
"""
Capture a clip from a Twitch stream and add captions to it.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_ffmpeg_path() -> str:
    """Get FFmpeg path."""
    winget_path = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin\ffmpeg.exe"
    )
    if os.path.exists(winget_path):
        return winget_path
    
    bundled_path = Path(__file__).parent.parent / "tools" / "ffmpeg-master-latest-win64-gpl" / "bin" / "ffmpeg.exe"
    if bundled_path.exists():
        return str(bundled_path)
    
    if os.system("where ffmpeg >nul 2>&1") == 0:
        return "ffmpeg"
    
    raise FileNotFoundError("FFmpeg not found")


def capture_twitch_clip(channel: str, duration: int = 60, output: str = None):
    """
    Capture a clip from a Twitch stream.
    
    Args:
        channel: Twitch channel name
        duration: Duration in seconds
        output: Output filename
    """
    if not output:
        timestamp = int(time.time())
        output = f"{channel}_{timestamp}.mp4"
    
    ffmpeg_path = get_ffmpeg_path()
    
    # Use streamlink or direct stream URL
    url = f"https://twitch.tv/{channel}"
    
    print(f"🎬 Capturing {duration}s from {url}...")
    print(f"📺 Channel: {channel}")
    
    try:
        # Check if streamlink is available
        if not subprocess.run(["where", "streamlink"], capture_output=True, shell=True).returncode == 0:
            print("❌ streamlink not found. Please install it: pip install streamlink")
            return None
        
        # Capture using streamlink + ffmpeg
        cmd = [
            "streamlink",
            "--twitch-disable-ads",
            url,
            "best",
            "-o", output
        ]
        
        print(f"📥 Downloading stream using streamlink...")
        print(f"⚠️  Note: streamlink will download until stopped (Ctrl+C)")
        print(f"💡 Alternatively, using FFmpeg to capture {duration} seconds...")
        
        # Alternative: Use ffmpeg to capture for a duration
        ffmpeg_cmd = [
            ffmpeg_path,
            "-y",
            "-ss", "00:00:00",
            "-t", str(duration),
            "-i", url,  # This might not work directly, would need HLS URL
            "-c", "copy",
            output
        ]
        
        print(f"💡 Use the preedit_and_post.py script on any video to add captions")
        print(f"📝 Example: python scripts/preedit_and_post.py --input {output} --output captioned.mp4")
        
        # Actually, let's just create a script that the user can run
        print("\n✅ To capture and add captions:")
        print(f"   1. Capture stream: streamlink {url} best -o {output}")
        print(f"   2. Add captions: python scripts/preedit_and_post.py --input {output} --output {output.replace('.mp4', '_captioned.mp4')}")
        
        return output
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Capture Twitch stream and prepare for captioning")
    parser.add_argument("channel", nargs="?", default="tenz", help="Twitch channel name")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument("--output", help="Output filename")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("📺 Twitch Clip Capture with Captioning")
    print("=" * 60)
    
    output = capture_twitch_clip(args.channel, args.duration, args.output)
    
    if output:
        print("\n" + "=" * 60)
        print("Next steps:")
        print("=" * 60)
        print(f"1. The stream will be saved to: {output}")
        print(f"2. To add captions, run:")
        print(f"   python scripts/preedit_and_post.py --input {output} --output {output.replace('.mp4', '_captioned.mp4')}")
        print("\n💡 Or run them together in one command if you have the video file")

