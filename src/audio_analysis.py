#!/usr/bin/env python3
"""
Audio Analysis Module for Clip Detection
Extracts audio-derived features to enhance moment detection across all content types.
"""

import numpy as np
import librosa
import soundfile as sf
from typing import Dict, Tuple, Optional
import logging
from pathlib import Path
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AudioAnalyzer:
    """Analyzes audio segments to extract features for clip-worthiness detection"""
    
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate
        
    def extract_audio_features(self, audio_path: str, start_time: float = None, end_time: float = None) -> Dict:
        """
        Extract comprehensive audio features from an audio segment.
        
        Args:
            audio_path: Path to audio file
            start_time: Start time in seconds (optional)
            end_time: End time in seconds (optional)
            
        Returns:
            Dict containing audio features
        """
        try:
            # Load audio file with explicit backend to avoid warnings
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            # Extract segment if time bounds provided
            if start_time is not None or end_time is not None:
                start_sample = int(start_time * sr) if start_time else 0
                end_sample = int(end_time * sr) if end_time else len(y)
                y = y[start_sample:end_sample]
            
            # Calculate features
            features = {
                "volume_avg": self._calculate_volume_avg(y),
                "volume_max": self._calculate_volume_max(y),
                "tempo": self._calculate_tempo(y, sr),
                "pause_duration": self._calculate_pause_duration(y, sr),
                "segment_duration": len(y) / sr,
                "energy_bursts": self._detect_energy_bursts(y, sr),
                "audience_reaction": self._detect_audience_reaction(y, sr),
                "volume_shifts": self._detect_volume_shifts(y, sr),
                "speech_rate": self._estimate_speech_rate(y, sr),
                "emotional_intensity": self._calculate_emotional_intensity(y, sr)
            }
            
            logger.info(f"✅ Extracted audio features from {audio_path}")
            return features
            
        except Exception as e:
            logger.error(f"❌ Error extracting audio features from {audio_path}: {e}")
            return self._get_default_features()
    
    def _calculate_volume_avg(self, y: np.ndarray) -> float:
        """Calculate average volume (RMS)"""
        rms = np.sqrt(np.mean(y**2))
        return float(rms)
    
    def _calculate_volume_max(self, y: np.ndarray) -> float:
        """Calculate maximum volume"""
        return float(np.max(np.abs(y)))
    
    def _calculate_tempo(self, y: np.ndarray, sr: int) -> float:
        """Calculate tempo in words per second (estimated)"""
        try:
            # Use onset detection to estimate speech tempo
            onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
            onset_times = librosa.frames_to_time(onset_frames, sr=sr)
            
            if len(onset_times) > 1:
                # Calculate average time between onsets
                intervals = np.diff(onset_times)
                avg_interval = np.mean(intervals)
                
                # Convert to estimated words per second
                # Assuming each onset represents roughly a word or syllable
                words_per_second = 1.0 / avg_interval if avg_interval > 0 else 0
                return min(words_per_second, 5.0)  # Cap at reasonable rate
            else:
                return 0.0
        except:
            return 0.0
    
    def _calculate_pause_duration(self, y: np.ndarray, sr: int) -> float:
        """Calculate total pause duration in seconds"""
        try:
            # Use voice activity detection to find speech segments
            # Simple threshold-based approach
            threshold = 0.01
            speech_mask = np.abs(y) > threshold
            
            # Find gaps (pauses)
            pause_samples = np.sum(~speech_mask)
            pause_duration = pause_samples / sr
            
            return float(pause_duration)
        except:
            return 0.0
    
    def _detect_energy_bursts(self, y: np.ndarray, sr: int) -> Dict:
        """Detect sudden bursts of energy"""
        try:
            # Calculate energy over time
            hop_length = 512
            energy = librosa.feature.rms(y=y, hop_length=hop_length)[0]
            
            # Find peaks (bursts)
            peaks, _ = librosa.effects.hpss(y)
            peak_energy = np.sqrt(np.mean(peaks**2))
            
            # Calculate burst intensity
            burst_threshold = np.mean(energy) + 2 * np.std(energy)
            burst_count = np.sum(energy > burst_threshold)
            
            return {
                "burst_count": int(burst_count),
                "burst_intensity": float(peak_energy),
                "has_bursts": burst_count > 0
            }
        except:
            return {"burst_count": 0, "burst_intensity": 0.0, "has_bursts": False}
    
    def _detect_audience_reaction(self, y: np.ndarray, sr: int) -> Dict:
        """Detect audience reactions (background noise, laughter, etc.)"""
        try:
            # Analyze frequency content for audience sounds
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            
            # Look for patterns typical of audience reactions
            # High frequency content often indicates laughter, applause
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            high_freq_energy = np.mean(spectral_centroid[spectral_centroid > 2000])
            
            # Detect laughter-like patterns
            laughter_score = self._detect_laughter_patterns(y, sr)
            
            return {
                "audience_present": high_freq_energy > 0.08,  # Lowered from 0.1
                "laughter_detected": laughter_score > 0.4,  # Lowered from 0.5
                "background_noise_level": float(np.mean(spectral_centroid)),
                "reaction_intensity": float(laughter_score)
            }
        except:
            return {
                "audience_present": False,
                "laughter_detected": False,
                "background_noise_level": 0.0,
                "reaction_intensity": 0.0
            }
    
    def _detect_laughter_patterns(self, y: np.ndarray, sr: int) -> float:
        """Detect laughter-like audio patterns"""
        try:
            # Laughter typically has specific frequency characteristics
            # Look for repetitive patterns in high frequencies
            hop_length = 512
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length)[0]
            
            # High rolloff values indicate laughter-like sounds
            laughter_indicators = spectral_rolloff > 0.6  # Lowered from 0.7
            laughter_score = np.mean(laughter_indicators)
            
            return float(laughter_score)
        except:
            return 0.0
    
    def _detect_volume_shifts(self, y: np.ndarray, sr: int) -> Dict:
        """Detect sudden volume shifts"""
        try:
            # Calculate volume over time
            hop_length = 512
            rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
            
            # Find sudden changes
            rms_diff = np.diff(rms)
            shift_threshold = np.std(rms) * 2
            
            # Count significant shifts
            shifts = np.abs(rms_diff) > shift_threshold
            shift_count = np.sum(shifts)
            
            # Calculate shift intensity
            shift_intensity = np.mean(np.abs(rms_diff[shifts])) if np.any(shifts) else 0
            
            return {
                "shift_count": int(shift_count),
                "shift_intensity": float(shift_intensity),
                "has_shifts": shift_count > 0,
                "max_shift": float(np.max(np.abs(rms_diff)))
            }
        except:
            return {
                "shift_count": 0,
                "shift_intensity": 0.0,
                "has_shifts": False,
                "max_shift": 0.0
            }
    
    def _estimate_speech_rate(self, y: np.ndarray, sr: int) -> float:
        """Estimate speech rate in words per second"""
        try:
            # Use pitch detection to estimate speech rate
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            
            # Count pitch changes (rough proxy for speech rate)
            pitch_changes = np.sum(np.diff(pitches, axis=1) != 0)
            duration = len(y) / sr
            
            # Estimate words per second
            words_per_second = pitch_changes / duration if duration > 0 else 0
            return min(words_per_second, 5.0)  # Cap at reasonable rate
        except:
            return 0.0
    
    def _calculate_emotional_intensity(self, y: np.ndarray, sr: int) -> float:
        """Calculate emotional intensity based on audio characteristics"""
        try:
            # Multiple factors contribute to emotional intensity
            # Volume variation, pitch variation, spectral features
            
            # Volume variation
            rms = librosa.feature.rms(y=y, hop_length=512)[0]
            volume_variation = np.std(rms)
            
            # Pitch variation
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
            pitch_variation = np.std(pitches[magnitudes > 0.1])
            
            # Spectral features
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            spectral_variation = np.std(spectral_centroid)
            
            # Combine factors
            intensity = (volume_variation * 0.4 + 
                        pitch_variation * 0.3 + 
                        spectral_variation * 0.3)
            
            return float(intensity)
        except:
            return 0.0
    
    def _get_default_features(self) -> Dict:
        """Return default features when analysis fails"""
        return {
            "volume_avg": 0.0,
            "volume_max": 0.0,
            "tempo": 0.0,
            "pause_duration": 0.0,
            "segment_duration": 0.0,
            "energy_bursts": {"burst_count": 0, "burst_intensity": 0.0, "has_bursts": False},
            "audience_reaction": {
                "audience_present": False,
                "laughter_detected": False,
                "background_noise_level": 0.0,
                "reaction_intensity": 0.0
            },
            "volume_shifts": {
                "shift_count": 0,
                "shift_intensity": 0.0,
                "has_shifts": False,
                "max_shift": 0.0
            },
            "speech_rate": 0.0,
            "emotional_intensity": 0.0
        }

def _convert_numpy_types(obj):
    """Convert numpy types to Python types for JSON serialization"""
    import numpy as np
    
    if isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: _convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_convert_numpy_types(item) for item in obj]
    else:
        return obj

def analyze_clip_audio(audio_path: str, transcript: str = None) -> Dict:
    """
    Analyze audio for clip-worthiness indicators.
    
    Args:
        audio_path: Path to audio file
        transcript: Optional transcript for context
        
    Returns:
        Dict with audio features and clip-worthiness indicators
    """
    analyzer = AudioAnalyzer()
    features = analyzer.extract_audio_features(audio_path)
    
    # Convert numpy types to Python types for JSON serialization
    features = _convert_numpy_types(features)
    
    # Apply thresholds to create boolean indicators with lower thresholds for more sensitivity
    indicators = {
        "energy_burst_detected": bool(features["energy_bursts"]["has_bursts"]),
        "audience_reaction_present": bool(features["audience_reaction"]["audience_present"]),
        "laughter_detected": bool(features["audience_reaction"]["laughter_detected"]),
        "high_emotional_intensity": bool(features["emotional_intensity"] > 0.25),  # Lowered from 0.3 to 0.25
        "rapid_speech": bool(features["speech_rate"] > 1.8),  # Lowered from 2.0 to 1.8
        "significant_pause": bool(features["pause_duration"] > 0.5)  # Lowered from 0.6 to 0.5
    }
    
    # Add comprehensive debug logging for each indicator with enhanced detail
    print(f"🔍 DEBUG: energy_burst_detected - Raw: {features['energy_bursts']['has_bursts']}, Result: {indicators['energy_burst_detected']}")
    print(f"🔍 DEBUG: audience_reaction_present - Raw: {features['audience_reaction']['audience_present']}, Result: {indicators['audience_reaction_present']}")
    print(f"🔍 DEBUG: laughter_detected - Raw: {features['audience_reaction']['laughter_detected']}, Result: {indicators['laughter_detected']}")
    print(f"🔍 DEBUG: high_emotional_intensity - Raw: {features['emotional_intensity']:.4f}, Threshold: 0.25, Result: {indicators['high_emotional_intensity']}")
    print(f"🔍 DEBUG: rapid_speech - Raw: {features['speech_rate']:.4f}, Threshold: 1.8, Result: {indicators['rapid_speech']}")
    print(f"🔍 DEBUG: significant_pause - Raw: {features['pause_duration']:.4f}, Threshold: 0.5, Result: {indicators['significant_pause']}")
    
    # Combine features and indicators
    result = {
        "audio_features": features,
        "clip_indicators": indicators,
        "overall_audio_score": _calculate_audio_score(features, indicators)
    }
    
    return result

def _calculate_audio_score(features: Dict, indicators: Dict) -> float:
    """Calculate overall audio-based clip-worthiness score"""
    score = 0.0
    
    # Volume-based indicators
    if indicators.get("energy_burst_detected", False):
        score += 0.25
    
    # Audience reaction indicators
    if indicators.get("audience_reaction_present", False):
        score += 0.2
    if indicators.get("laughter_detected", False):
        score += 0.15
    
    # Emotional intensity
    if indicators.get("high_emotional_intensity", False):
        score += 0.2
    
    # Speech patterns
    if indicators.get("rapid_speech", False):
        score += 0.1
    if indicators.get("significant_pause", False):
        score += 0.1
    
    return min(score, 1.0)  # Cap at 1.0

if __name__ == "__main__":
    # Test the audio analyzer
    test_audio = "test_audio.wav"
    if os.path.exists(test_audio):
        result = analyze_clip_audio(test_audio)
        print("Audio Analysis Result:")
        print(f"Overall Score: {result['overall_audio_score']:.3f}")
        print(f"Clip Indicators: {result['clip_indicators']}")
    else:
        print("Test audio file not found. Create a test_audio.wav file to test.") 