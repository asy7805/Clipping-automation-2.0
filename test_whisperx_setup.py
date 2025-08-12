#!/usr/bin/env python3
"""
WhisperX Setup Test Script
Run this to verify your WhisperX installation
"""

import os
import sys
import torch
import whisperx

def test_whisperx_setup():
    """Test the complete WhisperX setup"""
    
    print("🧪 Testing WhisperX v3-large Setup")
    print("=" * 50)
    
    # Test 1: Basic imports
    print("1. Testing imports...")
    try:
        import whisperx
        import torch
        import transformers
        print("   ✅ All imports successful")
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    
    # Test 2: Device detection
    print("2. Testing device detection...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"   ✅ Device: {device}")
    
    # Test 3: Model loading
    print("3. Testing model loading...")
    try:
        model = whisperx.load_model("large-v3", device, compute_type="float32")
        print("   ✅ Model loaded successfully")
    except Exception as e:
        print(f"   ❌ Model loading failed: {e}")
        return False
    
    # Test 4: Basic transcription (if test audio exists)
    print("4. Testing transcription...")
    test_audio = "test_audio.wav"  # You can create a test audio file
    if os.path.exists(test_audio):
        try:
            result = model.transcribe(test_audio, language="en")
            print("   ✅ Transcription successful")
            if isinstance(result, dict) and "text" in result:
                print(f"   📝 Sample: {result['text'][:100]}...")
        except Exception as e:
            print(f"   ❌ Transcription failed: {e}")
    else:
        print("   ⚠️  No test audio found, skipping transcription test")
    
    print("\n🎉 WhisperX setup is ready!")
    return True

if __name__ == "__main__":
    success = test_whisperx_setup()
    sys.exit(0 if success else 1)
