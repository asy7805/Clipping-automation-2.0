import subprocess
import time
from pathlib import Path

def merge_segments(segments, output_path):
    # segments are Path objects
    sorted_segments = sorted(segments, key=lambda p: p.stat().st_mtime)
    list_file = output_path.parent / "merge_list.txt"

    with open(list_file, "w") as f:
        for seg in sorted_segments:
            f.write(f"file '{seg.as_posix()}'\n")   # ✅ convert to POSIX string here

    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path)
    ], check=True)
    list_file.unlink()


def delete_from_supabase(sb, bucket, file_name, prefix, channel, stream_uid):
    """Delete a segment from Supabase storage by key."""
    day = time.strftime("%Y%m%d")
    key = f"{prefix}/{channel}/{stream_uid}/{day}/{file_name}"
    try:
        sb.storage.from_(bucket).remove([key])
        print(f"🗑️ Deleted from Supabase: {key}")
    except Exception as e:
        print(f"⚠️ Failed to delete {key} from Supabase: {e}")
        


import os
import re
import numpy as np
import librosa
import torch
from transformers import pipeline
import whisper
import tempfile
import subprocess

# ------------------ CONFIG ------------------
WHISPER_MODEL_NAME = "small"
EMOTION_MODEL_NAME = "SamLowe/roberta-base-go_emotions"  # better than distilbert-emotion
SAMPLE_RATE = 16000
MIN_AUDIO_THRESHOLD = 0.01   # skip low volume segments
ENERGY_WEIGHT = 0.35
PITCH_WEIGHT = 0.25
EMOTION_WEIGHT = 0.4
KEYWORD_BOOST = 0.15

# --------------------------------------------

# Load models globally
print("🧠 Loading Whisper and Emotion model...")
whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
emotion_pipeline = pipeline("text-classification", model=EMOTION_MODEL_NAME, top_k=1)
print("✅ Models loaded.")

# Common hype words
HYPE_WORDS = [
    "wow", "no way", "omg", "let's go", "wtf", "oh my god", "unbelievable",
    "insane", "noooo", "what", "brooo", "crazy", "bro", "woah", "damn"
]
HYPE_REGEX = re.compile(r"\b(" + "|".join([re.escape(w) for w in HYPE_WORDS]) + r")\b", re.I)

# ------------------ AUDIO ANALYSIS ------------------

def extract_audio_features(file_path: str):
    """Return RMS energy and pitch variance of audio segment."""
    y, sr = librosa.load(file_path, sr=SAMPLE_RATE, mono=True)
    if len(y) == 0:
        return 0, 0
    rms = np.mean(librosa.feature.rms(y=y))
    try:
        pitch, _, _ = librosa.pyin(y, fmin=80, fmax=400)
        pitch_var = np.nanstd(pitch)
    except Exception:
        pitch_var = 0
    return float(rms), float(pitch_var)


# ------------------ TEXT EMOTION ------------------

def transcribe_and_emotion(file_path: str):
    """Transcribe audio and get emotion intensity score."""
    transcript = whisper_model.transcribe(file_path, language="en", fp16=False)["text"].strip()
    if not transcript:
        return transcript, 0.0
    emotions = emotion_pipeline(transcript)
    if emotions and isinstance(emotions, list) and len(emotions) > 0:
        score = emotions[0][0]["score"]
    else:
        score = 0.0
    return transcript, score


# ------------------ SCORING ------------------

def compute_interest_score(file_path: str):
    """Compute final interest score for the segment."""
    energy, pitch_var = extract_audio_features(file_path)

    if energy < MIN_AUDIO_THRESHOLD:
        return 0.0, "", {"energy": energy, "pitch": pitch_var, "emotion": 0, "keyword": 0}

    transcript, emotion_score = transcribe_and_emotion(file_path)

    # Keyword excitement boost
    keyword_boost = 0
    if HYPE_REGEX.search(transcript):
        keyword_boost = KEYWORD_BOOST

    final_score = (
        ENERGY_WEIGHT * min(energy * 10, 1) +  # normalize roughly
        PITCH_WEIGHT * min(pitch_var, 1) +
        EMOTION_WEIGHT * emotion_score +
        keyword_boost
    )

    details = {
        "energy": round(energy, 4),
        "pitch": round(pitch_var, 4),
        "emotion": round(emotion_score, 4),
        "keyword": keyword_boost
    }
    return final_score, transcript, details


# ------------------ TOP-K SELECTION ------------------

def select_best_segments(segment_paths, top_k=5, min_score=0.3):
    """Return top_k segments with highest interest score."""
    scored_segments = []
    for path in segment_paths:
        score, transcript, detail = compute_interest_score(path)
        print(f"🎧 {os.path.basename(path)} | Score: {score:.3f} | {detail} | {transcript[:60]}...")
        if score >= min_score:
            scored_segments.append((path, score, transcript, detail))
    scored_segments.sort(key=lambda x: x[1], reverse=True)
    return scored_segments[:top_k]


if __name__ == "__main__":
    # Example usage
    test_files = [
        "seg_00001.mp4",
        "seg_00002.mp4",
        "seg_00003.mp4"
    ]
    best = select_best_segments(test_files, top_k=2)
    print("\n🏆 Top segments:")
    for b in best:
        print(f"{b[0]} => Score {b[1]:.3f} | Emotion {b[3]['emotion']} | Energy {b[3]['energy']}")


