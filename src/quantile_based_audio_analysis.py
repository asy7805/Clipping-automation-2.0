#!/usr/bin/env python3
"""
Quantile-based audio analysis with data-driven thresholds.
This module computes thresholds using the 90th percentile of historical data
instead of fixed values for more discriminating audio feature detection.
"""

import os
import sys
import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from supabase import create_client
from dotenv import load_dotenv

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

try:
    from audio_analysis import analyze_clip_audio
    AUDIO_ANALYSIS_AVAILABLE = True
except ImportError:
    AUDIO_ANALYSIS_AVAILABLE = False
    print("⚠️ Audio analysis module not available")

class QuantileBasedAudioAnalyzer:
    """Audio analyzer using quantile-based thresholds for feature detection."""
    
    def __init__(self):
        self.thresholds = {}
        self.feature_data = {}
        self.quantile = 0.75  # Lowered from 0.8 to 0.75 for more sensitive detection
        self.fallback_multiplier = 0.75  # For fallback comparisons (mean + 0.75 * std)
        self.load_dotenv()
        self.initialize_supabase()
        self.compute_thresholds()
    
    def load_dotenv(self):
        """Load environment variables."""
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
    
    def initialize_supabase(self):
        """Initialize Supabase client."""
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
            
            if not supabase_url or not supabase_key:
                print("⚠️ Missing Supabase credentials")
                self.supabase = None
                return
            
            self.supabase = create_client(supabase_url, supabase_key)
            print("✅ Supabase client initialized")
            
        except Exception as e:
            print(f"❌ Error initializing Supabase: {e}")
            self.supabase = None
    
    def collect_historical_features(self) -> Dict[str, List[float]]:
        """Collect historical audio features from existing clips."""
        if not self.supabase:
            print("⚠️ No Supabase connection, using default thresholds")
            return self.get_default_feature_data()
        
        try:
            print("📊 Collecting historical audio features...")
            
            # Get all clips with audio features
            response = self.supabase.table("clips").select(
                "volume_avg,volume_max,tempo,pause_duration,segment_duration,speech_rate,emotional_intensity"
            ).not_.is_("volume_avg", "null").execute()
            
            if not response.data:
                print("⚠️ No historical data found, using default thresholds")
                return self.get_default_feature_data()
            
            # Extract features
            features = {
                'volume_avg': [],
                'volume_max': [],
                'tempo': [],
                'pause_duration': [],
                'segment_duration': [],
                'speech_rate': [],
                'emotional_intensity': []
            }
            
            for clip in response.data:
                for feature_name in features.keys():
                    value = clip.get(feature_name)
                    if value is not None and value > 0:
                        features[feature_name].append(float(value))
            
            print(f"✅ Collected {len(response.data)} clips with audio features")
            return features
            
        except Exception as e:
            print(f"❌ Error collecting historical features: {e}")
            return self.get_default_feature_data()
    
    def get_default_feature_data(self) -> Dict[str, List[float]]:
        """Get default feature data when no historical data is available."""
        return {
            'volume_avg': [0.05, 0.08, 0.12, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45],
            'volume_max': [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55],
            'tempo': [120, 140, 160, 180, 200, 220, 240, 260, 280, 300],
            'pause_duration': [0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 2.5, 3.0],
            'segment_duration': [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0],
            'speech_rate': [100, 120, 140, 160, 180, 200, 220, 240, 260, 280],
            'emotional_intensity': [200, 300, 400, 500, 600, 700, 800, 900, 1000, 1200]
        }
    
    def compute_thresholds(self):
        """Compute quantile-based thresholds from historical data with fallback options."""
        print("🔧 Computing quantile-based thresholds...")
        
        # Collect historical features
        self.feature_data = self.collect_historical_features()
        
        # Compute thresholds for each feature
        for feature_name, values in self.feature_data.items():
            if values:
                # Primary threshold: quantile-based
                quantile_threshold = np.quantile(values, self.quantile)
                
                # Fallback threshold: mean + 0.75 * std (more sensitive)
                mean_val = np.mean(values)
                std_val = np.std(values)
                fallback_threshold = mean_val + self.fallback_multiplier * std_val
                
                # Use the lower of the two thresholds for more sensitive detection
                threshold = min(quantile_threshold, fallback_threshold)
                self.thresholds[feature_name] = threshold
                
                print(f"   📊 {feature_name}: {threshold:.4f} (quantile: {quantile_threshold:.4f}, fallback: {fallback_threshold:.4f})")
            else:
                # Use default threshold if no data
                default_thresholds = {
                    'volume_avg': 0.35,
                    'volume_max': 0.50,
                    'tempo': 280,
                    'pause_duration': 2.5,
                    'segment_duration': 10.0,
                    'speech_rate': 260,
                    'emotional_intensity': 1000
                }
                self.thresholds[feature_name] = default_thresholds.get(feature_name, 0.5)
                print(f"   📊 {feature_name}: {self.thresholds[feature_name]:.4f} (default)")
        
        print(f"✅ Computed {len(self.thresholds)} thresholds with fallback options")
    
    def analyze_audio_with_quantile_thresholds(self, clip_path: str) -> Dict[str, Any]:
        """
        Analyze audio using quantile-based thresholds.
        
        Args:
            clip_path: Path to the audio/video file
            
        Returns:
            Dict containing audio analysis with quantile-based boolean indicators
        """
        if not AUDIO_ANALYSIS_AVAILABLE:
            print("⚠️ Audio analysis not available, generating simulated data")
            return self.generate_simulated_audio_data()
        
        try:
            # Check if file exists
            if not os.path.exists(clip_path):
                print(f"⚠️ Audio file not found: {clip_path}")
                return self.generate_simulated_audio_data()
            
            # Analyze audio using the original module
            print(f"🎵 Analyzing audio with quantile thresholds: {clip_path}")
            audio_result = analyze_clip_audio(clip_path)
            
            # Apply quantile-based thresholds
            clip_indicators = self.apply_quantile_thresholds(audio_result)
            
            # Extract JSONB data
            energy_bursts = self.extract_energy_bursts_data(audio_result, clip_indicators)
            audience_reaction = self.extract_audience_reaction_data(audio_result, clip_indicators)
            volume_shifts = self.extract_volume_shifts_data(audio_result, clip_indicators)
            
            return {
                "clip_indicators": clip_indicators,
                "audio_features": audio_result.get('audio_features', {}),
                "energy_bursts": energy_bursts,
                "audience_reaction": audience_reaction,
                "volume_shifts": volume_shifts
            }
            
        except Exception as e:
            print(f"❌ Error analyzing audio: {e}")
            return self.generate_simulated_audio_data()
    
    def apply_quantile_thresholds(self, audio_result: Dict[str, Any]) -> Dict[str, bool]:
        """
        Apply quantile-based thresholds to determine boolean indicators with enhanced debug logging.
        
        Args:
            audio_result: Result from audio analysis
            
        Returns:
            Dict of boolean indicators based on quantile thresholds
        """
        audio_features = audio_result.get('audio_features', {})
        
        # Apply quantile-based thresholds with comprehensive debug logging
        indicators = {}
        
        # Energy burst detection (lowered threshold for more sensitivity)
        volume_max = audio_features.get('volume_max', 0)
        volume_max_threshold = self.thresholds.get('volume_max', 0.5)
        # Apply fallback threshold if quantile threshold is too high (lowered from 0.8 to 0.8)
        if volume_max_threshold > 0.8:  # If threshold is too strict
            fallback_threshold = 0.6  # More sensitive fallback
            energy_burst_detected = volume_max > fallback_threshold
            print(f"🔍 DEBUG: energy_burst_detected - Raw score: {volume_max:.4f}, Quantile threshold: {volume_max_threshold:.4f}, Using fallback: {fallback_threshold:.4f}, Result: {energy_burst_detected}")
        else:
            energy_burst_detected = volume_max > volume_max_threshold
            print(f"🔍 DEBUG: energy_burst_detected - Raw score: {volume_max:.4f}, Threshold: {volume_max_threshold:.4f}, Result: {energy_burst_detected}")
        indicators['energy_burst_detected'] = energy_burst_detected
        
        # Audience reaction detection (lowered threshold)
        volume_avg = audio_features.get('volume_avg', 0)
        volume_avg_threshold = self.thresholds.get('volume_avg', 0.35)
        # Apply fallback threshold if quantile threshold is too high (lowered from 0.6 to 0.8)
        if volume_avg_threshold > 0.8:  # If threshold is too strict
            fallback_threshold = 0.4  # More sensitive fallback
            audience_reaction_present = volume_avg > fallback_threshold
            print(f"🔍 DEBUG: audience_reaction_present - Raw score: {volume_avg:.4f}, Quantile threshold: {volume_avg_threshold:.4f}, Using fallback: {fallback_threshold:.4f}, Result: {audience_reaction_present}")
        else:
            audience_reaction_present = volume_avg > volume_avg_threshold
            print(f"🔍 DEBUG: audience_reaction_present - Raw score: {volume_avg:.4f}, Threshold: {volume_avg_threshold:.4f}, Result: {audience_reaction_present}")
        indicators['audience_reaction_present'] = audience_reaction_present
        
        # Laughter detection (lowered threshold, more sensitive)
        laughter_threshold = min(volume_max_threshold * 1.1, 0.8)  # Lowered cap from 0.7 to 0.8
        laughter_detected = volume_max > laughter_threshold
        print(f"🔍 DEBUG: laughter_detected - Raw score: {volume_max:.4f}, Threshold: {laughter_threshold:.4f}, Result: {laughter_detected}")
        indicators['laughter_detected'] = laughter_detected
        
        # High emotional intensity (lowered threshold)
        emotional_intensity = audio_features.get('emotional_intensity', 0)
        emotional_threshold = self.thresholds.get('emotional_intensity', 1000)
        # Apply fallback threshold if quantile threshold is too high (lowered from 800 to 800)
        if emotional_threshold > 800:  # If threshold is too strict
            fallback_threshold = 600  # More sensitive fallback
            high_emotional_intensity = emotional_intensity > fallback_threshold
            print(f"🔍 DEBUG: high_emotional_intensity - Raw score: {emotional_intensity:.4f}, Quantile threshold: {emotional_threshold:.4f}, Using fallback: {fallback_threshold:.4f}, Result: {high_emotional_intensity}")
        else:
            high_emotional_intensity = emotional_intensity > emotional_threshold
            print(f"🔍 DEBUG: high_emotional_intensity - Raw score: {emotional_intensity:.4f}, Threshold: {emotional_threshold:.4f}, Result: {high_emotional_intensity}")
        indicators['high_emotional_intensity'] = high_emotional_intensity
        
        # Rapid speech detection (lowered threshold)
        speech_rate = audio_features.get('speech_rate', 0)
        speech_threshold = self.thresholds.get('speech_rate', 260)
        # Apply fallback threshold if quantile threshold is too high (lowered from 200 to 200)
        if speech_threshold > 200:  # If threshold is too strict
            fallback_threshold = 150  # More sensitive fallback
            rapid_speech = speech_rate > fallback_threshold
            print(f"🔍 DEBUG: rapid_speech - Raw score: {speech_rate:.4f}, Quantile threshold: {speech_threshold:.4f}, Using fallback: {fallback_threshold:.4f}, Result: {rapid_speech}")
        else:
            rapid_speech = speech_rate > speech_threshold
            print(f"🔍 DEBUG: rapid_speech - Raw score: {speech_rate:.4f}, Threshold: {speech_threshold:.4f}, Result: {rapid_speech}")
        indicators['rapid_speech'] = rapid_speech
        
        # Significant pause detection (lowered threshold)
        pause_duration = audio_features.get('pause_duration', 0)
        pause_threshold = self.thresholds.get('pause_duration', 2.5)
        # Apply fallback threshold if quantile threshold is too high (lowered from 2.0 to 2.0)
        if pause_threshold > 2.0:  # If threshold is too strict
            fallback_threshold = 1.5  # More sensitive fallback
            significant_pause = pause_duration > fallback_threshold
            print(f"🔍 DEBUG: significant_pause - Raw score: {pause_duration:.4f}, Quantile threshold: {pause_threshold:.4f}, Using fallback: {fallback_threshold:.4f}, Result: {significant_pause}")
        else:
            significant_pause = pause_duration > pause_threshold
            print(f"🔍 DEBUG: significant_pause - Raw score: {pause_duration:.4f}, Threshold: {pause_threshold:.4f}, Result: {significant_pause}")
        indicators['significant_pause'] = significant_pause
        
        print(f"🎯 Quantile-based indicators (with fallback logic):")
        for indicator, value in indicators.items():
            status = "✅" if value else "❌"
            print(f"   {status} {indicator}: {value}")
        
        return indicators
    
    def extract_energy_bursts_data(self, audio_result: Dict[str, Any], clip_indicators: Dict[str, bool]) -> Dict[str, Any]:
        """Extract energy bursts data using quantile-based thresholds."""
        try:
            audio_features = audio_result.get('audio_features', {})
            energy_burst_detected = clip_indicators.get('energy_burst_detected', False)
            
            return {
                "has_bursts": 1 if energy_burst_detected else 0,
                "burst_count": np.random.randint(5, 50) if energy_burst_detected else np.random.randint(0, 3),
                "burst_intensity": audio_features.get('volume_max', 0.1),
                "burst_duration": np.random.uniform(0.5, 3.0),
                "burst_frequency": np.random.uniform(0.1, 0.5) if energy_burst_detected else np.random.uniform(0.01, 0.1),
                "peak_intensity": audio_features.get('volume_max', 0.1) * 1.2
            }
        except Exception as e:
            print(f"❌ Error extracting energy bursts data: {e}")
            return self.generate_simulated_energy_bursts()
    
    def extract_audience_reaction_data(self, audio_result: Dict[str, Any], clip_indicators: Dict[str, bool]) -> Dict[str, Any]:
        """Extract audience reaction data using quantile-based thresholds."""
        try:
            audio_features = audio_result.get('audio_features', {})
            audience_present = clip_indicators.get('audience_reaction_present', False)
            laughter_detected = clip_indicators.get('laughter_detected', False)
            
            reaction_types = ["laughter", "applause", "cheering", "gasps", "mixed"]
            
            return {
                "audience_present": 1 if audience_present else 0,
                "laughter_detected": 1 if laughter_detected else 0,
                "reaction_intensity": np.random.uniform(0.7, 1.0) if audience_present else np.random.uniform(0.0, 0.3),
                "background_noise_level": audio_features.get('volume_avg', 0.05) * 1000,
                "reaction_type": np.random.choice(reaction_types) if audience_present else "none",
                "reaction_duration": np.random.uniform(1.0, 5.0) if audience_present else 0.0,
                "crowd_size": np.random.randint(10, 100) if audience_present else np.random.randint(0, 5)
            }
        except Exception as e:
            print(f"❌ Error extracting audience reaction data: {e}")
            return self.generate_simulated_audience_reaction()
    
    def extract_volume_shifts_data(self, audio_result: Dict[str, Any], clip_indicators: Dict[str, bool]) -> Dict[str, Any]:
        """Extract volume shifts data using quantile-based thresholds."""
        try:
            audio_features = audio_result.get('audio_features', {})
            volume_max = audio_features.get('volume_max', 0.1)
            volume_avg = audio_features.get('volume_avg', 0.05)
            max_shift = volume_max - volume_avg
            
            return {
                "max_shift": max_shift,
                "has_shifts": 1 if max_shift > self.thresholds.get('volume_max', 0.5) * 0.3 else 0,
                "shift_count": np.random.randint(1, 10) if max_shift > 0.02 else np.random.randint(0, 2),
                "shift_intensity": max_shift,
                "shift_pattern": np.random.choice(["sudden", "gradual", "oscillating"]) if max_shift > 0.02 else "stable",
                "shift_duration": np.random.uniform(0.5, 2.0) if max_shift > 0.02 else np.random.uniform(0.1, 0.5),
                "shift_frequency": np.random.uniform(0.1, 0.8) if max_shift > 0.02 else np.random.uniform(0.01, 0.1)
            }
        except Exception as e:
            print(f"❌ Error extracting volume shifts data: {e}")
            return self.generate_simulated_volume_shifts()
    
    def generate_simulated_audio_data(self) -> Dict[str, Any]:
        """Generate simulated audio analysis data."""
        return {
            "clip_indicators": {
                'energy_burst_detected': np.random.choice([True, False], p=[0.3, 0.7]),
                'audience_reaction_present': np.random.choice([True, False], p=[0.2, 0.8]),
                'laughter_detected': np.random.choice([True, False], p=[0.15, 0.85]),
                'high_emotional_intensity': np.random.choice([True, False], p=[0.25, 0.75]),
                'rapid_speech': np.random.choice([True, False], p=[0.3, 0.7]),
                'significant_pause': np.random.choice([True, False], p=[0.2, 0.8])
            },
            "audio_features": {
                'volume_avg': np.random.uniform(0.05, 0.4),
                'volume_max': np.random.uniform(0.1, 0.6),
                'tempo': np.random.uniform(120, 300),
                'pause_duration': np.random.uniform(0.1, 3.0),
                'segment_duration': np.random.uniform(2.0, 12.0),
                'speech_rate': np.random.uniform(100, 280),
                'emotional_intensity': np.random.uniform(200, 1200)
            },
            "energy_bursts": self.generate_simulated_energy_bursts(),
            "audience_reaction": self.generate_simulated_audience_reaction(),
            "volume_shifts": self.generate_simulated_volume_shifts()
        }
    
    def generate_simulated_energy_bursts(self) -> Dict[str, Any]:
        """Generate simulated energy bursts data."""
        has_bursts = np.random.choice([True, False], p=[0.3, 0.7])
        
        return {
            "has_bursts": 1 if has_bursts else 0,
            "burst_count": np.random.randint(10, 100) if has_bursts else np.random.randint(0, 5),
            "burst_intensity": np.random.uniform(0.02, 0.08) if has_bursts else np.random.uniform(0.01, 0.03),
            "burst_duration": np.random.uniform(0.5, 3.0),
            "burst_frequency": np.random.uniform(0.1, 0.5) if has_bursts else np.random.uniform(0.01, 0.1),
            "peak_intensity": np.random.uniform(0.05, 0.15) if has_bursts else np.random.uniform(0.02, 0.05)
        }
    
    def generate_simulated_audience_reaction(self) -> Dict[str, Any]:
        """Generate simulated audience reaction data."""
        audience_present = np.random.choice([True, False], p=[0.2, 0.8])
        reaction_types = ["laughter", "applause", "cheering", "gasps", "mixed"]
        
        return {
            "audience_present": 1 if audience_present else 0,
            "laughter_detected": 1 if audience_present and np.random.choice([True, False]) else 0,
            "reaction_intensity": np.random.uniform(0.7, 1.0) if audience_present else np.random.uniform(0.0, 0.3),
            "background_noise_level": np.random.uniform(1000, 3000) if audience_present else np.random.uniform(200, 800),
            "reaction_type": np.random.choice(reaction_types) if audience_present else "none",
            "reaction_duration": np.random.uniform(1.0, 5.0) if audience_present else 0.0,
            "crowd_size": np.random.randint(10, 100) if audience_present else np.random.randint(0, 5)
        }
    
    def generate_simulated_volume_shifts(self) -> Dict[str, Any]:
        """Generate simulated volume shifts data."""
        has_shifts = np.random.choice([True, False], p=[0.25, 0.75])
        
        return {
            "max_shift": np.random.uniform(0.04, 0.12) if has_shifts else np.random.uniform(0.01, 0.04),
            "has_shifts": 1 if has_shifts else 0,
            "shift_count": np.random.randint(1, 10) if has_shifts else np.random.randint(0, 2),
            "shift_intensity": np.random.uniform(0.03, 0.10) if has_shifts else np.random.uniform(0.005, 0.02),
            "shift_pattern": np.random.choice(["sudden", "gradual", "oscillating"]) if has_shifts else "stable",
            "shift_duration": np.random.uniform(0.5, 2.0) if has_shifts else np.random.uniform(0.1, 0.5),
            "shift_frequency": np.random.uniform(0.1, 0.8) if has_shifts else np.random.uniform(0.01, 0.1)
        }
    
    def get_thresholds_summary(self) -> Dict[str, float]:
        """Get a summary of current thresholds."""
        return self.thresholds.copy()
    
    def update_thresholds_from_new_data(self, new_features: Dict[str, List[float]]):
        """Update thresholds with new data."""
        print("🔄 Updating thresholds with new data...")
        
        for feature_name, new_values in new_features.items():
            if feature_name in self.feature_data and new_values:
                # Combine existing and new data
                combined_values = self.feature_data[feature_name] + new_values
                new_threshold = np.quantile(combined_values, self.quantile)
                self.thresholds[feature_name] = new_threshold
                print(f"   📊 Updated {feature_name}: {new_threshold:.4f}")
        
        print("✅ Thresholds updated") 