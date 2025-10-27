#!/usr/bin/env python3
"""
Video captioning script that adds captions to raw footage.

This script:
1. Transcribes the video audio using WhisperX
2. Generates an SRT subtitle file
3. Burns captions into the video using FFmpeg

Usage:
    python preedit_and_post.py --input video.mp4 --output video_with_captions.mp4
    python preedit_and_post.py --input video.mp4 --output video_with_captions.mp4 --style modern
"""

import os
import sys
import subprocess
import argparse
import whisperx
import torch
from pathlib import Path
from typing import List, Tuple, Optional

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_ffmpeg_path() -> str:
    """Get FFmpeg path, checking Windows installation first."""
    # Check for WinGet FFmpeg installation
    winget_path = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin\ffmpeg.exe"
    )
    if os.path.exists(winget_path):
        return winget_path
    
    # Check for bundled FFmpeg
    bundled_path = Path(__file__).parent.parent / "tools" / "ffmpeg-master-latest-win64-gpl" / "bin" / "ffmpeg.exe"
    if bundled_path.exists():
        return str(bundled_path)
    
    # Check if ffmpeg is in PATH
    if os.system("where ffmpeg >nul 2>&1") == 0:
        return "ffmpeg"
    
    raise FileNotFoundError("FFmpeg not found. Please install FFmpeg.")


def transcribe_video(video_path: str, model_name: str = "large-v3") -> Optional[dict]:
    """
    Transcribe video audio using WhisperX.
    
    Args:
        video_path: Path to the video file
        model_name: WhisperX model to use
        
    Returns:
        Transcription result dictionary or None if failed
    """
    try:
        # Extract audio using ffmpeg
        temp_audio = Path(video_path).with_suffix('.temp.wav')
        
        ffmpeg_path = get_ffmpeg_path()
        print(f"🔧 Using FFmpeg: {ffmpeg_path}")
        
        cmd = [
            ffmpeg_path, '-y',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',
            '-ar', '16000',  # 16kHz sample rate (optimal for WhisperX)
            '-ac', '1',      # Mono audio
            '-loglevel', 'warning',
            str(temp_audio)
        ]
        
        print("🎤 Extracting audio from video with FFmpeg...")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        
        if result.returncode != 0:
            print(f"❌ Failed to extract audio: {result.stderr[:500]}")
            return None
        
        if not temp_audio.exists():
            print("❌ Audio extraction failed - output file not created")
            return None
        
        # Load WhisperX model
        print(f"📥 Loading WhisperX model: {model_name}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisperx.load_model(model_name, device, compute_type="float32")
        print(f"✅ Model loaded on {device}")
        
        # Transcribe
        print("🎤 Transcribing audio...")
        print(f"   Audio file: {temp_audio} (exists: {temp_audio.exists()}, size: {temp_audio.stat().st_size if temp_audio.exists() else 0} bytes)")
        # Use absolute path and convert to string
        audio_path = str(temp_audio.absolute())
        print(f"   Transcribing: {audio_path}")
        transcription = model.transcribe(audio_path, language="en")
        
        # Clean up temporary audio
        if temp_audio.exists():
            temp_audio.unlink()
        
        print("✅ Transcription complete")
        return transcription
        
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return None


def create_srt_file(transcription: dict, output_path: str) -> bool:
    """
    Create SRT subtitle file from WhisperX transcription.
    
    Args:
        transcription: WhisperX transcription result
        output_path: Path to save SRT file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        segments = transcription.get("segments", [])
        if not segments:
            print("⚠️  No segments found in transcription")
            return False
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments, 1):
                start = segment.get('start', 0.0)
                end = segment.get('end', 0.0)
                text = segment.get('text', '').strip()
                
                # Convert seconds to SRT time format (HH:MM:SS,mmm)
                start_time = format_srt_time(start)
                end_time = format_srt_time(end)
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")
        
        print(f"✅ SRT file created: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating SRT file: {e}")
        return False


def format_srt_time(seconds: float) -> str:
    """
    Convert seconds to SRT time format (HH:MM:SS,mmm).
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted time string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def burn_captions(video_path: str, srt_path: str, output_path: str, style: str = "default") -> bool:
    """
    Burn captions into video using FFmpeg with proper Windows path handling.
    
    Args:
        video_path: Input video file
        srt_path: SRT subtitle file
        output_path: Output video file
        style: Caption style ('default', 'modern', 'bold', 'minimal')
        
    Returns:
        True if successful, False otherwise
    """
    try:
        ffmpeg_path = get_ffmpeg_path()
        
        # Define subtitle styles for FFmpeg's force_style
        styles = {
            "default": "FontName=Arial,FontSize=20,PrimaryColour=&Hffffff,BackColour=&H80000000,Bold=1,Outline=2,Shadow=1",
            "modern": "FontName=Arial Black,FontSize=22,PrimaryColour=&Hffffff,BackColour=&H80000000,Bold=1,Outline=3,Shadow=2",
            "bold": "FontName=Arial Black,FontSize=24,PrimaryColour=&H00ffff,BackColour=&H80000000,Bold=1,Outline=4,Shadow=3",
            "minimal": "FontName=Arial,FontSize=18,PrimaryColour=&Hffffff,BackColour=&H00000000,Bold=0,Outline=1,Shadow=0"
        }
        
        style_options = styles.get(style, styles["default"])
        
        # Normalize paths for ffmpeg subtitle filter
        # Convert to absolute paths and use forward slashes
        srt_abs = os.path.abspath(srt_path).replace('\\', '/')
        video_abs = os.path.abspath(video_path).replace('\\', '/')
        output_abs = os.path.abspath(output_path).replace('\\', '/')
        
        # Escape special characters for the filter
        srt_escaped = srt_abs.replace(':', '\\:')
        
        # Build ffmpeg command
        cmd = [
            ffmpeg_path, '-y',  # Overwrite output file
            '-i', video_abs,    # Input video
            '-vf', f"subtitles='{srt_escaped}':force_style='{style_options}'",  # Subtitle filter
            '-c:v', 'libx264',  # H.264 codec
            '-preset', 'medium',  # Encoding preset
            '-crf', '23',       # Quality setting
            '-c:a', 'copy',     # Copy audio stream
            output_abs
        ]
        
        print("🎬 Burning captions into video using FFmpeg...")
        print(f"   Input: {video_path}")
        print(f"   Subtitle: {srt_path}")
        print(f"   Output: {output_path}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        
        if result.returncode == 0:
            print(f"✅ Video with captions created: {output_path}")
            return True
        else:
            print(f"❌ FFmpeg failed (return code: {result.returncode})")
            if result.stderr:
                # Print last few lines of stderr for debugging
                stderr_lines = result.stderr.strip().split('\n')
                print("   Error output:")
                for line in stderr_lines[-5:]:
                    print(f"   {line}")
            return False
            
    except Exception as e:
        print(f"❌ Error burning captions: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Add captions to video footage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python preedit_and_post.py --input raw_footage.mp4 --output edited_with_captions.mp4
  python preedit_and_post.py --input video.mp4 --output captioned.mp4 --style modern
  python preedit_and_post.py --input video.mp4 --output captioned.mp4 --model small --style bold
        """
    )
    
    parser.add_argument('--input', '-i', required=True,
                       help='Input video file')
    parser.add_argument('--output', '-o', required=True,
                       help='Output video file with captions')
    parser.add_argument('--model', default='large-v3',
                       choices=['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'],
                       help='WhisperX model to use (default: large-v3)')
    parser.add_argument('--style', choices=['default', 'modern', 'bold', 'minimal'],
                       default='default',
                       help='Caption style (default: default)')
    parser.add_argument('--keep-srt', action='store_true',
                       help='Keep the SRT file after processing')
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input):
        print(f"❌ Input file not found: {args.input}")
        sys.exit(1)
    
    # Transcribe video
    transcription = transcribe_video(args.input, args.model)
    if not transcription:
        print("❌ Failed to transcribe video")
        sys.exit(1)
    
    # Create SRT file
    srt_path = Path(args.output).with_suffix('.srt')
    if not create_srt_file(transcription, str(srt_path)):
        print("❌ Failed to create SRT file")
        sys.exit(1)
    
    # Burn captions into video
    if not burn_captions(args.input, str(srt_path), args.output, args.style):
        print("❌ Failed to burn captions")
        sys.exit(1)
    
    # Clean up SRT file if not keeping it
    if not args.keep_srt and srt_path.exists():
        srt_path.unlink()
        print("🗑️  Cleaned up SRT file")
    
    print("\n✅ Complete! Video with captions created successfully.")


if __name__ == "__main__":
    main()
