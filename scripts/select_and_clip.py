import os
import re
import subprocess
import tempfile
import librosa
import numpy as np
import soundfile as sf
from dotenv import load_dotenv

# Fix tokenizer parallelism warning BEFORE importing transformers
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from transformers import pipeline
from faster_whisper import WhisperModel
from typing import List, Tuple
import torch

# -----------------------------------------
# 🔧 Load environment variables and models
# -----------------------------------------
load_dotenv()

# Cache models globally — loaded only once.
_whisper_model = None
_sentiment_pipeline = None

# ------------------ CONFIG (Optimized for Performance) ------------------
# Using smaller models to reduce CPU/GPU usage while maintaining accuracy
WHISPER_MODEL_NAME = "base"  # Balanced: better than tiny, faster than small (74M vs 244M params)
EMOTION_MODEL_NAME = "j-hartmann/emotion-english-distilroberta-base"  # Smaller, faster than RoBERTa-base
SAMPLE_RATE = 16000
MIN_AUDIO_THRESHOLD = 0.01   # Skip low volume segments
ENERGY_WEIGHT = 0.35
PITCH_WEIGHT = 0.25
EMOTION_WEIGHT = 0.4
KEYWORD_BOOST = 0.15
# Performance optimizations
USE_FAST_PITCH = True  # Use faster pitch estimation instead of librosa.pyin
PITCH_SKIP_THRESHOLD = 0.02  # Skip pitch analysis if energy is too low

# Common hype words (from past backend)
HYPE_WORDS = [
    "wow", "no way", "omg", "let's go", "wtf", "oh my god", "unbelievable",
    "insane", "noooo", "what", "brooo", "crazy", "bro", "woah", "damn"
]
HYPE_REGEX = re.compile(r"\b(" + "|".join([re.escape(w) for w in HYPE_WORDS]) + r")\b", re.I)
# ------------------------------------------------------------


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        print(f"🔊 Loading Whisper model ({WHISPER_MODEL_NAME})...")
        # Use CPU with int8 for lower memory usage (faster than float32, less memory than float16)
        _whisper_model = WhisperModel(
            WHISPER_MODEL_NAME, 
            device="cpu", 
            compute_type="int8",
            cpu_threads=1,  # Reduced to 1 thread to minimize CPU usage
            num_workers=1    # Single worker for lower memory
        )  
    return _whisper_model


def get_sentiment_pipeline():
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        print(f"🧠 Loading emotion model ({EMOTION_MODEL_NAME})...")
        _sentiment_pipeline = pipeline(
            "text-classification",
            model=EMOTION_MODEL_NAME,
            top_k=1,  # Get top emotion only for speed
            device=-1,  # Use CPU (device=-1), avoid GPU/MPS for lower power
            batch_size=1,  # Process one at a time to reduce memory
            truncation=True,
            max_length=128  # Limit input length for faster processing
        )
    return _sentiment_pipeline


# -----------------------------------------
# 🎧 Audio Extraction
# -----------------------------------------
def extract_audio_from_video(video_path: str) -> str:
    """Extracts mono 16kHz WAV audio from MP4 using ffmpeg."""
    wav_path = str(video_path).rsplit(".", 1)[0] + ".wav"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        wav_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed on {video_path}: {result.stderr.decode()}")
    return wav_path


# -----------------------------------------
# 🗣️ Speech-to-Text
# -----------------------------------------

def obtain_transcript(wav_path: str) -> str:
    """Transcribes audio using Whisper (small) model."""
    if _whisper_model is None:
        model = get_whisper_model()
    else:
        model = _whisper_model
    try:
        segments, info = model.transcribe(wav_path, beam_size=1)
        text = " ".join([segment.text.strip() for segment in segments if segment.text.strip()])
        print(text)
        return text
    except Exception as e:
        print(f"Error transcribing {wav_path}: {e}")
        return ""


# -----------------------------------------
# 💬 Emotion Detection from Transcript
# -----------------------------------------
def peaks_in_transcript(transcript: str, excitement_labels=None, intensity_factor=0.8) -> float:
    """
    Detects excitement or emotional intensity from text.
    Returns a normalized excitement score (0–1).
    """
    if not transcript or len(transcript.strip()) < 3:
        return 0.0

    sentences = re.split(r"(?<=[.!?])\s+", transcript.strip())
    sentences = [s for s in sentences if s]

    sentiment = get_sentiment_pipeline()
    results = sentiment(sentences)

    if excitement_labels is None:
        excitement_labels = {"joy", "surprise", "positive"}

    total_score, count = 0.0, 0
    for chunks in results:
        for res in chunks:
            label = res["label"].lower()
            score = res["score"]
            if label in excitement_labels:
                total_score += score
                count += 1
            elif label in {"anger", "fear", "sadness"}:
                total_score += score * intensity_factor
                count += 1

    return float(np.clip(total_score / count if count else 0.0, 0, 1))


# -----------------------------------------
# 🔊 Audio Spike Detection
# -----------------------------------------
def detect_audio_spikes(
    file_path: str,
    frame_duration: float = 0.5,
    energy_threshold_factor: float = 1.6,
    min_silence_duration: float = 1.0,
) -> List[Tuple[float, float]]:
    """Detects high-energy regions in an audio clip."""
    try:
        y, sr = librosa.load(file_path, sr=16000, mono=True)
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return []

    frame_len = int(frame_duration * sr)
    hop_len = frame_len // 2
    rms = librosa.feature.rms(y=y, frame_length=frame_len, hop_length=hop_len)[0]
    rms = (rms - np.min(rms)) / (np.max(rms) - np.min(rms) + 1e-6)

    threshold = np.mean(rms) * energy_threshold_factor
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_len)
    spike_frames = np.where(rms > threshold)[0]
    if len(spike_frames) == 0:
        return []

    spike_regions, start = [], spike_frames[0]
    for i in range(1, len(spike_frames)):
        if spike_frames[i] - spike_frames[i - 1] > 1:
            spike_regions.append((start, spike_frames[i - 1]))
            start = spike_frames[i]
    spike_regions.append((start, spike_frames[-1]))

    results = [
        (float(times[s]), float(times[e] + frame_duration)) for s, e in spike_regions
    ]

    # Merge close spikes
    merged = []
    for seg in results:
        if not merged:
            merged.append(seg)
        else:
            ps, pe = merged[-1]
            if seg[0] - pe <= min_silence_duration:
                merged[-1] = (ps, seg[1])
            else:
                merged.append(seg)
    return merged


# -----------------------------------------
# 🎯 Advanced Audio Feature Extraction (Past Backend)
# -----------------------------------------

def extract_audio_features(file_path: str):
    """Return RMS energy and pitch variance of audio segment (optimized for performance)."""
    try:
        y, sr = librosa.load(file_path, sr=SAMPLE_RATE, mono=True)
    except Exception as e:
        print(f"❌ Error loading audio {file_path}: {e}")
        return 0.0, 0.0
    
    if len(y) == 0:
        return 0.0, 0.0
    
    # RMS Energy (fast)
    rms = np.mean(librosa.feature.rms(y=y))
    
    # Skip expensive pitch analysis if energy is too low
    if rms < PITCH_SKIP_THRESHOLD:
        return float(rms), 0.0
    
    # Pitch Variance (optimized - use faster method if enabled)
    pitch_var = 0.0
    if USE_FAST_PITCH:
        # Faster pitch estimation using autocorrelation (much faster than pyin)
        try:
            # Use autocorrelation-based pitch detection (faster than pyin)
            pitches = librosa.yin(y, fmin=80, fmax=400, sr=sr)
            # Filter out NaN values
            valid_pitches = pitches[~np.isnan(pitches)]
            if len(valid_pitches) > 0:
                pitch_var = np.std(valid_pitches)
        except Exception as e:
            # Fallback to simple zero-crossing rate variance (very fast)
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            pitch_var = np.std(zcr) * 100  # Scale to similar range
    else:
        # Original pyin method (more accurate but much slower)
        try:
            pitch, _, _ = librosa.pyin(y, fmin=80, fmax=400, sr=sr)
            pitch_var = np.nanstd(pitch)
            if np.isnan(pitch_var):
                pitch_var = 0.0
        except Exception as e:
            print(f"⚠️ Pitch analysis failed: {e}")
            pitch_var = 0.0
    
    return float(rms), float(pitch_var)


def transcribe_and_emotion(file_path: str):
    """Transcribe audio and get emotion intensity score (Past Backend)."""
    transcript = obtain_transcript(file_path)
    
    if not transcript or len(transcript.strip()) < 3:
        return transcript, 0.0
    
    sentiment = get_sentiment_pipeline()
    try:
        emotions = sentiment(transcript)
        
        # Handle different output formats
        if emotions and isinstance(emotions, list) and len(emotions) > 0:
            # RoBERTa outputs [[{label, score}]]
            if isinstance(emotions[0], list):
                score = emotions[0][0]["score"]
            else:
                score = emotions[0]["score"]
        else:
            score = 0.0
    except Exception as e:
        print(f"⚠️ Emotion detection failed: {e}")
        score = 0.0
    
    return transcript, float(score)


def compute_interest_score(file_path: str):
    """
    Compute final interest score for the segment (Past Backend Algorithm).
    Returns: (score, transcript, details_dict)
    All breakdown scores are normalized to 0-1 range.
    """
    energy, pitch_var = extract_audio_features(file_path)

    # Normalize energy to 0-1 (RMS typically 0-0.1, multiply by 10 to get 0-1)
    normalized_energy = min(energy * 10, 1.0)
    
    # Normalize pitch variance to 0-1 (assuming max variance of ~50 Hz for human voice)
    # Pitch variance from librosa can be 0-100+ Hz, normalize to 0-1
    normalized_pitch = min(pitch_var / 50.0, 1.0) if pitch_var > 0 else 0.0

    # Skip if audio is too quiet
    if energy < MIN_AUDIO_THRESHOLD:
        return 0.0, "", {
            "energy": round(normalized_energy, 4),
            "pitch": round(normalized_pitch, 4),
            "emotion": 0.0,
            "keyword": 0.0
        }

    transcript, emotion_score = transcribe_and_emotion(file_path)

    # Normalize emotion score to 0-1 (clamp to ensure it's in range)
    normalized_emotion = min(max(emotion_score, 0.0), 1.0)

    # Keyword excitement boost (from past backend)
    keyword_boost = 0
    keyword_detected = False
    if HYPE_REGEX.search(transcript):
        keyword_boost = KEYWORD_BOOST
        keyword_detected = True
        print(f"🔥 Hype keywords detected!")
    
    # Normalize keyword to 0-1 (1.0 if detected, 0.0 if not)
    normalized_keyword = 1.0 if keyword_detected else 0.0

    # Past Backend's Weighted Scoring Formula (using normalized values)
    final_score = (
        ENERGY_WEIGHT * normalized_energy +      # 35% - normalized energy
        PITCH_WEIGHT * normalized_pitch +        # 25% - normalized pitch variance
        EMOTION_WEIGHT * normalized_emotion +    # 40% - normalized emotion intensity
        keyword_boost                            # 15% - keyword boost (raw value for scoring)
    )

    # Return normalized breakdown scores (all 0-1)
    details = {
        "energy": round(normalized_energy, 4),
        "pitch": round(normalized_pitch, 4),
        "emotion": round(normalized_emotion, 4),
        "keyword": round(normalized_keyword, 4)
    }
    
    return final_score, transcript, details


def is_interesting_segment(file_path: str, min_score: float = 0.3) -> bool:
    """
    Determine if segment is interesting using past backend's sophisticated algorithm.
    """
    try:
        score, transcript, details = compute_interest_score(file_path)
        
        snippet = transcript[:80] if transcript else "No transcript"
        print(f"🎧 Score: {score:.3f} | {details} | {snippet}...")
        
        return score >= min_score

    except Exception as e:
        print(f"⚠️ Error analyzing {file_path}: {e}")
        return False



# -----------------------------------------
# 🧪 Main Testing Entry
# -----------------------------------------
def detect_interest(video_path: str):
    """Main entry point for external calls."""
    try:
        audio_path = extract_audio_from_video(video_path)
        result = is_interesting_segment(audio_path)
        
        print(f"✅ Interesting: {result}")
        return result
    except RuntimeError as e:
        # FFmpeg failed - file is likely corrupted or incomplete
        print(f"⚠️ Skipping corrupted/incomplete file {video_path}: {e}")
        return False
    except Exception as e:
        # Any other error - log and skip
        print(f"⚠️ Error processing {video_path}: {e}")
        return False
    finally:
        # cleanup temporary wav if it exists
        wav_path = str(video_path).rsplit(".", 1)[0] + ".wav"
        if os.path.exists(wav_path):
            os.remove(wav_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python detect_interest.py <video_path>")
        exit(1)
    detect_interest(sys.argv[1])
