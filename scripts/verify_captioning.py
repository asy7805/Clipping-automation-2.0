#!/usr/bin/env python3
"""
Verify that the captioning system works correctly.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.preedit_and_post import (
    get_ffmpeg_path, 
    format_srt_time, 
    create_srt_file,
    transcribe_video
)

def verify_components():
    """Verify all components of the captioning system."""
    print("🔍 Verifying Captioning System Components...")
    print("=" * 60)
    
    # Test 1: FFmpeg detection
    try:
        ffmpeg = get_ffmpeg_path()
        print(f"✅ FFmpeg: {ffmpeg}")
    except Exception as e:
        print(f"❌ FFmpeg: {e}")
        return False
    
    # Test 2: Time formatting
    try:
        result = format_srt_time(125.5)
        expected = "00:02:05,500"
        if result == expected:
            print(f"✅ SRT time formatting: {result}")
        else:
            print(f"❌ SRT time formatting: Expected {expected}, got {result}")
            return False
    except Exception as e:
        print(f"❌ SRT time formatting: {e}")
        return False
    
    # Test 3: SRT file creation
    try:
        import tempfile
        test_transcription = {
            'segments': [
                {'start': 0.0, 'end': 2.5, 'text': 'Hello world'},
                {'start': 2.5, 'end': 5.0, 'text': 'This is a test'}
            ]
        }
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.srt', delete=False)
        f.close()
        
        result = create_srt_file(test_transcription, f.name)
        if result:
            content = open(f.name).read()
            if 'Hello world' in content and '00:00:00,000 --> 00:00:02,500' in content:
                print("✅ SRT file creation: Working correctly")
            else:
                print("❌ SRT file creation: Content incorrect")
                return False
        else:
            print("❌ SRT file creation: Failed")
            return False
        
        os.unlink(f.name)
    except Exception as e:
        print(f"❌ SRT file creation: {e}")
        return False
    
    # Test 4: WhisperX import
    try:
        import whisperx
        print("✅ WhisperX: Installed and importable")
    except Exception as e:
        print(f"❌ WhisperX: {e}")
        return False
    
    # Test 5: Script argument parsing
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "scripts/preedit_and_post.py", "--help"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and "Add captions to video footage" in result.stdout:
            print("✅ Script: Can be invoked with --help")
        else:
            print("❌ Script: Help command failed")
            return False
    except Exception as e:
        print(f"❌ Script: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL COMPONENTS VERIFIED AND WORKING")
    print("=" * 60)
    print("\n📝 Summary:")
    print("   • FFmpeg is detected and ready")
    print("   • SRT time formatting works correctly")
    print("   • SRT file generation works correctly")
    print("   • WhisperX is installed and ready")
    print("   • Script can be invoked")
    print("\n⚠️  Note: Cannot test video transcription without a valid video file")
    print("    The implementation is ready - provide a valid MP4 to test end-to-end")
    
    return True

if __name__ == "__main__":
    success = verify_components()
    sys.exit(0 if success else 1)

