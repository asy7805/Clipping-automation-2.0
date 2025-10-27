#!/usr/bin/env python3
"""
Smart captioning workflow:
1. Capture stream segments
2. Identify interesting moments
3. Add word-synced captions with precise timing
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


def get_word_level_timings(audio_path: str, model):
    """Get word-level timings for precise subtitle sync."""
    try:
        result = model.transcribe(audio_path, language="en")
        
        # Align for word-level timing
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_a, metadata = whisperx.load_align_model(
            language_code="en",
            device=device
        )
        
        aligned = whisperx.align(result["segments"], model_a, metadata, audio_path, device)
        
        return aligned
        
    except Exception as e:
        print(f"⚠️  Alignment failed: {e}")
        return result


def create_word_timed_srt(transcription, output_path: str):
    """Create SRT with word-level precision from aligned WhisperX output."""
    try:
        segments = transcription.get("segments", [])
        
        with open(output_path, 'w', encoding='utf-8') as f:
            sub_idx = 1
            
            for segment in segments:
                words = segment.get('words', [])
                
                # Group words into subtitle lines (max 2 lines, ~12 words each)
                current_line = []
                chars_in_line = 0
                
                for word in words:
                    word_text = word.get('word', '').strip()
                    start = word.get('start', 0)
                    end = word.get('end', 0)
                    chars_in_line += len(word_text)
                    
                    if not current_line:
                        line_start = start
                    
                    current_line.append((word_text, end))
                    chars_in_line += 1  # space
                    
                    # Create subtitle when line is full or segment ends
                    if chars_in_line > 60 or word == words[-1]:
                        line_end = end
                        
                        # Format times
                        start_time = format_srt_time(line_start)
                        end_time = format_srt_time(line_end)
                        
                        # Write subtitle
                        f.write(f"{sub_idx}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{' '.join([w[0] for w in current_line])}\n\n")
                        
                        sub_idx += 1
                        current_line = []
                        chars_in_line = 0
                    elif len(current_line) > 12:
                        # Force new line at word count
                        line_end = end
                        start_time = format_srt_time(line_start)
                        end_time = format_srt_time(line_end)
                        
                        f.write(f"{sub_idx}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{' '.join([w[0] for w in current_line])}\n\n")
                        
                        sub_idx += 1
                        current_line = []
                        chars_in_line = 0
        
        print(f"✅ Created word-synced SRT: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating SRT: {e}")
        return False


def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def process_clip_with_smart_captions(video_path: str, output_path: str):
    """Process a video with word-level precise captions."""
    ffmpeg = get_ffmpeg_path()
    
    # Extract audio
    audio_path = video_path.replace('.mp4', '.temp.wav')
    
    print("🎤 Extracting audio...")
    cmd = [
        ffmpeg, "-y",
        "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1",
        "-loglevel", "quiet",
        audio_path
    ]
    subprocess.run(cmd, capture_output=True)
    
    # Transcribe with word-level alignment
    print("📝 Transcribing with word-level alignment...")
    print("📥 Loading WhisperX model...")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = whisperx.load_model("tiny", device, compute_type="float32")
    
    transcription = model.transcribe(audio_path, language="en")
    
    # Align for word-level timing
    print("🔗 Aligning words for precise timing...")
    model_a, metadata = whisperx.load_align_model("en", device)
    aligned = whisperx.align(
        transcription["segments"],
        model_a, metadata, audio_path, device
    )
    
    # Create word-timed SRT
    srt_path = output_path.replace('.mp4', '.srt')
    create_word_timed_srt(aligned, srt_path)
    
    # Burn captions
    print("🎬 Burning word-synced captions...")
    
    srt_abs = os.path.abspath(srt_path).replace('\\', '/')
    video_abs = os.path.abspath(video_path).replace('\\', '/')
    output_abs = os.path.abspath(output_path).replace('\\', '/')
    srt_escaped = srt_abs.replace(':', '\\:')
    
    style = "FontName=Arial,FontSize=22,PrimaryColour=&Hffffff,BackColour=&H80000000,Bold=1,Outline=2,Shadow=1"
    
    cmd = [
        ffmpeg, "-y",
        "-i", video_abs,
        "-vf", f"subtitles='{srt_escaped}':force_style='{style}'",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "copy",
        output_abs
    ]
    
    subprocess.run(cmd, capture_output=True, text=True)
    
    # Cleanup
    if Path(audio_path).exists():
        Path(audio_path).unlink()
    
    print(f"✅ Complete: {output_path}")
    return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart captioning with word-level sync")
    parser.add_argument("input", help="Input video file")
    parser.add_argument("--output", help="Output video file")
    
    args = parser.parse_args()
    
    output = args.output or args.input.replace('.mp4', '_smart_captioned.mp4')
    
    # Ensure FFmpeg in PATH
    os.environ["PATH"] += f";{os.path.dirname(get_ffmpeg_path())}"
    
    process_clip_with_smart_captions(args.input, output)


if __name__ == "__main__":
    main()

