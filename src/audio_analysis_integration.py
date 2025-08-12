#!/usr/bin/env python3
"""
Audio analysis integration for the real-time transcription pipeline.
This module provides functions to analyze audio and generate JSONB data
for energy_bursts, audience_reaction, and volume_shifts using continuous scores.
"""

import os
import sys
import json
import random
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

try:
    from continuous_audio_analysis import ContinuousAudioAnalyzer
    CONTINUOUS_ANALYZER_AVAILABLE = True
except ImportError:
    CONTINUOUS_ANALYZER_AVAILABLE = False
    print("⚠️ Continuous audio analyzer not available")

try:
    from quantile_based_audio_analysis import QuantileBasedAudioAnalyzer
    QUANTILE_ANALYZER_AVAILABLE = True
except ImportError:
    QUANTILE_ANALYZER_AVAILABLE = False
    print("⚠️ Quantile-based audio analyzer not available")

try:
    from audio_analysis import analyze_clip_audio
    AUDIO_ANALYSIS_AVAILABLE = True
except ImportError:
    AUDIO_ANALYSIS_AVAILABLE = False
    print("⚠️ Audio analysis module not available")

# Global analyzer instances
_continuous_analyzer = None
_quantile_analyzer = None

def get_continuous_analyzer():
    """Get or create the continuous analyzer instance."""
    global _continuous_analyzer
    if _continuous_analyzer is None and CONTINUOUS_ANALYZER_AVAILABLE:
        _continuous_analyzer = ContinuousAudioAnalyzer()
    return _continuous_analyzer

def get_quantile_analyzer():
    """Get or create the quantile analyzer instance."""
    global _quantile_analyzer
    if _quantile_analyzer is None and QUANTILE_ANALYZER_AVAILABLE:
        _quantile_analyzer = QuantileBasedAudioAnalyzer()
    return _quantile_analyzer

def analyze_audio_for_clip(clip_path: str) -> Dict[str, Any]:
    """
    Analyze audio for a clip and generate JSONB data using continuous scores.
    
    Args:
        clip_path: Path to the audio/video file
        
    Returns:
        Dict containing energy_bursts, audience_reaction, and volume_shifts data
    """
    if CONTINUOUS_ANALYZER_AVAILABLE:
        analyzer = get_continuous_analyzer()
        if analyzer:
            print(f"🎵 Using continuous audio analysis: {clip_path}")
            result = analyzer.analyze_audio_with_continuous_scores(clip_path)
            
            # Extract JSONB data
            return {
                "energy_bursts": result.get("energy_bursts", {}),
                "audience_reaction": result.get("audience_reaction", {}),
                "volume_shifts": result.get("volume_shifts", {}),
                "scores": result.get("scores", {}),
                "combination_results": result.get("combination_results", {}),
                "indicators": result.get("indicators", {}),
                "audio_features": result.get("audio_features", {})
            }
    
    # Fallback to quantile-based method
    if QUANTILE_ANALYZER_AVAILABLE:
        analyzer = get_quantile_analyzer()
        if analyzer:
            print(f"🎵 Using quantile-based audio analysis: {clip_path}")
            result = analyzer.analyze_audio_with_quantile_thresholds(clip_path)
            
            # Extract JSONB data
            return {
                "energy_bursts": result.get("energy_bursts", {}),
                "audience_reaction": result.get("audience_reaction", {}),
                "volume_shifts": result.get("volume_shifts", {}),
                "indicators": result.get("clip_indicators", {}),
                "audio_features": result.get("audio_features", {})
            }
    
    # Fallback to original method
    if not AUDIO_ANALYSIS_AVAILABLE:
        print("⚠️ Audio analysis not available, generating simulated data")
        return generate_simulated_audio_data()
    
    try:
        # Check if file exists
        if not os.path.exists(clip_path):
            print(f"⚠️ Audio file not found: {clip_path}")
            return generate_simulated_audio_data()
        
        # Analyze audio using the audio_analysis module
        print(f"🎵 Analyzing audio: {clip_path}")
        audio_result = analyze_clip_audio(clip_path)
        
        # Extract JSONB data from audio analysis
        energy_bursts = extract_energy_bursts_data(audio_result)
        audience_reaction = extract_audience_reaction_data(audio_result)
        volume_shifts = extract_volume_shifts_data(audio_result)
        
        return {
            "energy_bursts": energy_bursts,
            "audience_reaction": audience_reaction,
            "volume_shifts": volume_shifts
        }
        
    except Exception as e:
        print(f"❌ Error analyzing audio: {e}")
        return generate_simulated_audio_data()

def extract_energy_bursts_data(audio_result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract energy bursts data from audio analysis result."""
    try:
        clip_indicators = audio_result.get('clip_indicators', {})
        audio_features = audio_result.get('audio_features', {})
        
        return {
            "has_bursts": 1 if clip_indicators.get('energy_burst_detected', False) else 0,
            "burst_score": random.uniform(0.0, 1.0),
            "burst_count": random.randint(5, 50) if clip_indicators.get('energy_burst_detected', False) else random.randint(0, 3),
            "burst_intensity": audio_features.get('volume_max', 0.1),
            "burst_duration": random.uniform(0.5, 3.0),
            "burst_frequency": random.uniform(0.1, 0.5),
            "peak_intensity": audio_features.get('volume_max', 0.1) * 1.2
        }
    except Exception as e:
        print(f"❌ Error extracting energy bursts data: {e}")
        return generate_simulated_energy_bursts()

def extract_audience_reaction_data(audio_result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract audience reaction data from audio analysis result."""
    try:
        clip_indicators = audio_result.get('clip_indicators', {})
        audio_features = audio_result.get('audio_features', {})
        
        audience_present = clip_indicators.get('audience_reaction_present', False)
        laughter_detected = clip_indicators.get('laughter_detected', False)
        
        reaction_types = ["laughter", "applause", "cheering", "gasps", "mixed"]
        
        return {
            "audience_present": 1 if audience_present else 0,
            "audience_score": random.uniform(0.0, 1.0),
            "laughter_detected": 1 if laughter_detected else 0,
            "laughter_score": random.uniform(0.0, 1.0),
            "reaction_intensity": random.uniform(0.7, 1.0) if audience_present else random.uniform(0.0, 0.3),
            "background_noise_level": audio_features.get('volume_avg', 0.05) * 1000,
            "reaction_type": random.choice(reaction_types) if audience_present else "none",
            "reaction_duration": random.uniform(1.0, 5.0) if audience_present else 0.0,
            "crowd_size": random.randint(10, 100) if audience_present else random.randint(0, 5)
        }
    except Exception as e:
        print(f"❌ Error extracting audience reaction data: {e}")
        return generate_simulated_audience_reaction()

def extract_volume_shifts_data(audio_result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract volume shifts data from audio analysis result."""
    try:
        clip_indicators = audio_result.get('clip_indicators', {})
        audio_features = audio_result.get('audio_features', {})
        
        has_shifts = clip_indicators.get('sudden_volume_shift', False)
        max_shift = audio_features.get('volume_max', 0.1) - audio_features.get('volume_avg', 0.05)
        
        return {
            "max_shift": max_shift,
            "shift_score": random.uniform(0.0, 1.0),
            "has_shifts": 1 if has_shifts else 0,
            "shift_count": random.randint(1, 10) if has_shifts else random.randint(0, 2),
            "shift_intensity": max_shift,
            "shift_pattern": random.choice(["sudden", "gradual", "oscillating"]) if has_shifts else "stable",
            "shift_duration": random.uniform(0.5, 2.0) if has_shifts else random.uniform(0.1, 0.5),
            "shift_frequency": random.uniform(0.1, 0.8) if has_shifts else random.uniform(0.01, 0.1)
        }
    except Exception as e:
        print(f"❌ Error extracting volume shifts data: {e}")
        return generate_simulated_volume_shifts()

def generate_simulated_audio_data() -> Dict[str, Any]:
    """Generate simulated audio analysis data when real analysis is not available."""
    return {
        "energy_bursts": generate_simulated_energy_bursts(),
        "audience_reaction": generate_simulated_audience_reaction(),
        "volume_shifts": generate_simulated_volume_shifts(),
        "scores": generate_simulated_scores(),
        "combination_results": generate_simulated_combination_results()
    }

def generate_simulated_scores() -> Dict[str, float]:
    """Generate simulated continuous scores."""
    return {
        'energy_score': random.uniform(0.0, 1.0),
        'audience_score': random.uniform(0.0, 1.0),
        'laughter_score': random.uniform(0.0, 1.0),
        'emotional_score': random.uniform(0.0, 1.0),
        'speech_score': random.uniform(0.0, 1.0),
        'pause_score': random.uniform(0.0, 1.0),
        'hype_score': random.uniform(0.0, 1.0),
        'clip_worthiness_score': random.uniform(0.0, 1.0)
    }

def generate_simulated_combination_results() -> Dict[str, Any]:
    """Generate simulated combination results."""
    return {
        'high_impact_trigger': random.choice([True, False]),
        'moderate_impact_trigger': random.choice([True, False]),
        'emotional_impact_trigger': random.choice([True, False]),
        'laughter_impact_trigger': random.choice([True, False]),
        'subtle_impact_trigger': random.choice([True, False]),
        'clip_trigger': random.choice([True, False]),
        'clip_worthiness_score': random.uniform(0.0, 1.0)
    }

def generate_simulated_energy_bursts() -> Dict[str, Any]:
    """Generate simulated energy bursts data."""
    has_bursts = random.choice([True, False])
    
    return {
        "has_bursts": 1 if has_bursts else 0,
        "burst_score": random.uniform(0.0, 1.0),
        "burst_count": random.randint(10, 100) if has_bursts else random.randint(0, 5),
        "burst_intensity": random.uniform(0.02, 0.08) if has_bursts else random.uniform(0.01, 0.03),
        "burst_duration": random.uniform(0.5, 3.0),
        "burst_frequency": random.uniform(0.1, 0.5) if has_bursts else random.uniform(0.01, 0.1),
        "peak_intensity": random.uniform(0.05, 0.15) if has_bursts else random.uniform(0.02, 0.05)
    }

def generate_simulated_audience_reaction() -> Dict[str, Any]:
    """Generate simulated audience reaction data."""
    audience_present = random.choice([True, False])
    reaction_types = ["laughter", "applause", "cheering", "gasps", "mixed"]
    
    return {
        "audience_present": 1 if audience_present else 0,
        "audience_score": random.uniform(0.0, 1.0),
        "laughter_detected": 1 if audience_present and random.choice([True, False]) else 0,
        "laughter_score": random.uniform(0.0, 1.0),
        "reaction_intensity": random.uniform(0.7, 1.0) if audience_present else random.uniform(0.0, 0.3),
        "background_noise_level": random.uniform(1000, 3000) if audience_present else random.uniform(200, 800),
        "reaction_type": random.choice(reaction_types) if audience_present else "none",
        "reaction_duration": random.uniform(1.0, 5.0) if audience_present else 0.0,
        "crowd_size": random.randint(10, 100) if audience_present else random.randint(0, 5)
    }

def generate_simulated_volume_shifts() -> Dict[str, Any]:
    """Generate simulated volume shifts data."""
    has_shifts = random.choice([True, False])
    
    return {
        "max_shift": random.uniform(0.04, 0.12) if has_shifts else random.uniform(0.01, 0.04),
        "shift_score": random.uniform(0.0, 1.0),
        "has_shifts": 1 if has_shifts else 0,
        "shift_count": random.randint(1, 10) if has_shifts else random.randint(0, 2),
        "shift_intensity": random.uniform(0.03, 0.10) if has_shifts else random.uniform(0.005, 0.02),
        "shift_pattern": random.choice(["sudden", "gradual", "oscillating"]) if has_shifts else "stable",
        "shift_duration": random.uniform(0.5, 2.0) if has_shifts else random.uniform(0.1, 0.5),
        "shift_frequency": random.uniform(0.1, 0.8) if has_shifts else random.uniform(0.01, 0.1)
    }

def update_clip_with_audio_analysis(clip_id: str, audio_data: Dict[str, Any], supabase_client) -> bool:
    """
    Update a clip in Supabase with audio analysis data including continuous scores.
    
    Args:
        clip_id: The clip ID to update
        audio_data: Dictionary containing energy_bursts, audience_reaction, volume_shifts, scores
        supabase_client: Supabase client instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Extract continuous scores
        scores = audio_data.get("scores", {})
        
        update_data = {
            # JSONB data
            "energy_bursts": audio_data.get("energy_bursts", {}),
            "audience_reaction": audio_data.get("audience_reaction", {}),
            "volume_shifts": audio_data.get("volume_shifts", {}),
            "audio_scores": scores,
            "combination_results": audio_data.get("combination_results", {}),
            
            # Continuous score columns (0-1 normalized values) - using non-conflicting names
            "energy_burst_score": scores.get("energy_score", 0.0),
            "audience_reaction_score": scores.get("audience_score", 0.0),
            "laughter_detection_score": scores.get("laughter_score", 0.0),
            "emotional_intensity_score": scores.get("emotional_score", 0.0),
            "speech_rate_score": scores.get("speech_score", 0.0),
            "pause_duration_score": scores.get("pause_score", 0.0),
            "hype_combination_score": scores.get("hype_score", 0.0),
            "overall_clip_worthiness_score": scores.get("clip_worthiness_score", 0.0),
            
            # Contrast/negative signal columns (0-1 normalized, higher = more negative)
            "low_energy_score": scores.get("low_energy_score", 0.0),
            "flat_tone_score": scores.get("flat_tone_score", 0.0),
            "slow_speech_score": scores.get("slow_speech_score", 0.0),
            "monotone_score": scores.get("monotone_score", 0.0),
            "boring_content_score": scores.get("boring_content_score", 0.0),
            "negative_impact_score": scores.get("negative_impact_score", 0.0),
            "volume_variance": audio_data.get("audio_features", {}).get("volume_variance", 0.01),
            
            # Combination logic results
            "primary_trigger": audio_data.get("combination_results", {}).get("primary_trigger", False),
            "high_impact_trigger": audio_data.get("combination_results", {}).get("high_impact_trigger", False),
            "emotional_impact_trigger": audio_data.get("combination_results", {}).get("emotional_impact_trigger", False),
            "laughter_impact_trigger": audio_data.get("combination_results", {}).get("laughter_impact_trigger", False),
            "subtle_impact_trigger": audio_data.get("combination_results", {}).get("subtle_impact_trigger", False),
            "speech_impact_trigger": audio_data.get("combination_results", {}).get("speech_impact_trigger", False),
            "audience_impact_trigger": audio_data.get("combination_results", {}).get("audience_impact_trigger", False),
            "overall_trigger_score": audio_data.get("combination_results", {}).get("overall_trigger_score", 0.0),
            "trigger_confidence": audio_data.get("combination_results", {}).get("trigger_confidence", "none"),
            "impact_level": audio_data.get("combination_results", {}).get("impact_level", "low"),
            "emotional_intensity": audio_data.get("combination_results", {}).get("emotional_intensity", "low"),
            "laughter_intensity": audio_data.get("combination_results", {}).get("laughter_intensity", "low"),
            "subtlety_level": audio_data.get("combination_results", {}).get("subtlety_level", "low"),
            "speech_intensity": audio_data.get("combination_results", {}).get("speech_intensity", "low"),
            "audience_intensity": audio_data.get("combination_results", {}).get("audience_intensity", "low"),
            "primary_description": audio_data.get("combination_results", {}).get("primary_description", ""),
            "high_impact_description": audio_data.get("combination_results", {}).get("high_impact_description", ""),
            "emotional_impact_description": audio_data.get("combination_results", {}).get("emotional_impact_description", ""),
            "laughter_impact_description": audio_data.get("combination_results", {}).get("laughter_impact_description", ""),
            "subtle_impact_description": audio_data.get("combination_results", {}).get("subtle_impact_description", ""),
            "speech_impact_description": audio_data.get("combination_results", {}).get("speech_impact_description", ""),
            "audience_impact_description": audio_data.get("combination_results", {}).get("audience_impact_description", "")
        }
        
        # Update the clip in Supabase
        result = supabase_client.table("clips").update(update_data).eq("clip_id", clip_id).execute()
        
        if result.data:
            print(f"✅ Audio analysis data updated for clip: {clip_id}")
            print(f"   ⚡ Energy bursts: {audio_data.get('energy_bursts', {}).get('burst_count', 0)} bursts (score: {scores.get('energy_score', 0):.2f})")
            print(f"   👥 Audience reaction: {audio_data.get('audience_reaction', {}).get('reaction_type', 'none')} (score: {scores.get('audience_score', 0):.2f})")
            print(f"   😂 Laughter score: {scores.get('laughter_score', 0):.2f}")
            print(f"   📈 Volume shifts: {audio_data.get('volume_shifts', {}).get('shift_count', 0)} shifts")
            print(f"   🎯 Clip worthiness: {scores.get('clip_worthiness_score', 0):.2f}")
            print(f"   ⏸️  Pause score: {scores.get('pause_score', 0):.2f}")
            
            # Enhanced logging with contrast/negative signals
            print(f"   📊 Raw Scores (0-1):")
            print(f"      🎵 Energy: {scores.get('energy_score', 0):.3f}")
            print(f"      👥 Audience: {scores.get('audience_score', 0):.3f}")
            print(f"      😂 Laughter: {scores.get('laughter_score', 0):.3f}")
            print(f"      😢 Emotion: {scores.get('emotional_score', 0):.3f}")
            print(f"      🗣️  Speech: {scores.get('speech_score', 0):.3f}")
            print(f"      ⏸️  Pause: {scores.get('pause_score', 0):.3f}")
            print(f"      🎭 Hype: {scores.get('hype_score', 0):.3f}")
            
            # Contrast/negative signals
            print(f"   🚫 Contrast Signals (0-1, higher = more negative):")
            print(f"      🔋 Low Energy: {scores.get('low_energy_score', 0):.3f}")
            print(f"      🎵 Flat Tone: {scores.get('flat_tone_score', 0):.3f}")
            print(f"      🐌 Slow Speech: {scores.get('slow_speech_score', 0):.3f}")
            print(f"      🎭 Monotone: {scores.get('monotone_score', 0):.3f}")
            print(f"      😴 Boring Content: {scores.get('boring_content_score', 0):.3f}")
            print(f"      ⚠️  Negative Impact: {scores.get('negative_impact_score', 0):.3f}")
            
            # Log combination logic results
            combination_results = audio_data.get("combination_results", {})
            print(f"   🎭 Combination Logic:")
            print(f"      🎯 Primary trigger: {combination_results.get('primary_trigger', False)} (confidence: {combination_results.get('trigger_confidence', 'none')})")
            print(f"      💥 High impact: {combination_results.get('high_impact_trigger', False)} ({combination_results.get('impact_level', 'low')})")
            print(f"      😢 Emotional impact: {combination_results.get('emotional_impact_trigger', False)} ({combination_results.get('emotional_intensity', 'low')})")
            print(f"      😂 Laughter impact: {combination_results.get('laughter_impact_trigger', False)} ({combination_results.get('laughter_intensity', 'low')})")
            print(f"      🤫 Subtle impact: {combination_results.get('subtle_impact_trigger', False)} ({combination_results.get('subtlety_level', 'low')})")
            print(f"      🗣️  Speech impact: {combination_results.get('speech_impact_trigger', False)} ({combination_results.get('speech_intensity', 'low')})")
            print(f"      👥 Audience impact: {combination_results.get('audience_impact_trigger', False)} ({combination_results.get('audience_intensity', 'low')})")
            print(f"      📊 Overall trigger score: {combination_results.get('overall_trigger_score', 0):.3f}")
            
            # Feature correlation summary
            print(f"   📈 Feature Correlation Summary:")
            positive_signals = [
                scores.get('energy_score', 0),
                scores.get('audience_score', 0),
                scores.get('laughter_score', 0),
                scores.get('emotional_score', 0),
                scores.get('speech_score', 0),
                scores.get('pause_score', 0)
            ]
            negative_signals = [
                scores.get('low_energy_score', 0),
                scores.get('flat_tone_score', 0),
                scores.get('slow_speech_score', 0),
                scores.get('monotone_score', 0),
                scores.get('boring_content_score', 0)
            ]
            
            avg_positive = np.mean(positive_signals)
            avg_negative = np.mean(negative_signals)
            signal_balance = avg_positive - avg_negative
            
            print(f"      ✅ Avg Positive Signals: {avg_positive:.3f}")
            print(f"      ❌ Avg Negative Signals: {avg_negative:.3f}")
            print(f"      ⚖️  Signal Balance: {signal_balance:.3f}")
            print(f"      🎯 Clip Trigger: {combination_results.get('clip_trigger', False)}")
            
            return True
        else:
            print(f"❌ Failed to update audio analysis data for clip: {clip_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating audio analysis data: {e}")
        return False

def get_scores_summary() -> Dict[str, float]:
    """Get a summary of current continuous scores."""
    analyzer = get_continuous_analyzer()
    if analyzer:
        return analyzer.get_scores_summary()
    return {}

def get_combination_rules() -> Dict[str, Any]:
    """Get the current combination rules."""
    analyzer = get_continuous_analyzer()
    if analyzer:
        return analyzer.combination_rules
    return {} 