import os
import re
import subprocess
import tempfile
import librosa
import numpy as np
import soundfile as sf
from dotenv import load_dotenv
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


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        print("🔊 Loading Whisper model (small)...")
        _whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")  
    return _whisper_model


def get_sentiment_pipeline():
    global _sentiment_pipeline
    if _sentiment_pipeline is None:
        print("🧠 Loading DistilBERT emotion model...")
        _sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model="bhadresh-savani/distilbert-base-uncased-emotion",
            batch_size=16,
            truncation=True,
            top_k=None,
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
# 🎯 Interest Detection (Hybrid)
# -----------------------------------------

def get_emotion_excitement(text):
    sentiment = get_sentiment_pipeline()
    results = sentiment(text)

    # Normalize list-of-lists output
    if isinstance(results, list):
        if len(results) > 0 and isinstance(results[0], list):
            results = results[0]
        results = results[0]

    label = results["label"]
    score = results["score"]

    # Map excitement-like emotions higher
    if label in ["joy", "excitement", "surprise", "anger"]:
        return score
    else:
        return 0.0


def is_interesting_segment(file_path: str, min_audio_spike_time: float = 1.5) -> bool:
    try:
        spikes = detect_audio_spikes(file_path)
        total_spike_time = sum(e - s for s, e in spikes)
        print(f"🎧 Spike duration: {total_spike_time:.2f}s")

        if total_spike_time < 0.3:
            print("😴 Very low energy — not interesting.")
            return False

        transcript = obtain_transcript(file_path)
        excitement = peaks_in_transcript(transcript)
        normalized_energy = min(total_spike_time / 4.0, 1.0)

        final_score = 0.5 * normalized_energy + 0.5 * excitement
        print(f"🔎 Energy={normalized_energy:.2f}, Excitement={excitement:.2f}, Final={final_score:.2f}")

        return final_score > 0.3 or excitement > 0.4

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
