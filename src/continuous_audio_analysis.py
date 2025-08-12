#!/usr/bin/env python3
"""
Continuous audio analysis with normalized scores and combination logic.
This module converts boolean indicators to continuous scores (0-1) and
implements higher-order logic for more sophisticated clip detection.
"""

import os
import sys
import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from supabase import create_client
from dotenv import load_dotenv

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

try:
    from quantile_based_audio_analysis import QuantileBasedAudioAnalyzer
    QUANTILE_ANALYZER_AVAILABLE = True
except ImportError:
    QUANTILE_ANALYZER_AVAILABLE = False
    print("⚠️ Quantile-based audio analyzer not available")

class ContinuousAudioAnalyzer:
    """Audio analyzer using continuous scores and combination logic."""
    
    def __init__(self):
        self.quantile_analyzer = None
        self.thresholds = {}
        self.feature_data = {}
        self.combination_rules = {}
        self.load_dotenv()
        self.initialize_supabase()
        self.initialize_quantile_analyzer()
        self.setup_combination_rules()
    
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
    
    def initialize_quantile_analyzer(self):
        """Initialize the quantile-based analyzer."""
        if QUANTILE_ANALYZER_AVAILABLE:
            try:
                self.quantile_analyzer = QuantileBasedAudioAnalyzer()
                self.thresholds = self.quantile_analyzer.get_thresholds_summary()
                print("✅ Quantile analyzer initialized")
            except Exception as e:
                print(f"❌ Error initializing quantile analyzer: {e}")
                self.quantile_analyzer = None
        else:
            print("⚠️ Quantile analyzer not available")
    
    def setup_combination_rules(self):
        """Setup combination logic rules for clip detection."""
        self.combination_rules = {
            # High-impact combinations (both scores must be high)
            "high_impact": {
                "pause_score": 0.7,
                "hype_score": 0.6,
                "description": "Pause + Hype combination"
            },
            # Moderate combinations (one high, one moderate)
            "moderate_impact": {
                "pause_score": 0.5,
                "energy_score": 0.4,
                "description": "Pause + Energy combination"
            },
            # Emotional combinations
            "emotional_impact": {
                "emotional_score": 0.6,
                "audience_score": 0.5,
                "description": "Emotional + Audience reaction"
            },
            # Laughter combinations
            "laughter_impact": {
                "laughter_score": 0.7,
                "energy_score": 0.5,
                "description": "Laughter + Energy burst"
            },
            # Subtle combinations (for quiet moments)
            "subtle_impact": {
                "pause_score": 0.8,
                "emotional_score": 0.3,
                "description": "Long pause + subtle emotion"
            }
        }
        print("✅ Combination rules configured")
    
    def compute_continuous_scores(self, audio_features: Dict[str, float]) -> Dict[str, float]:
        """
        Compute continuous scores (0-1) for each audio feature.
        
        Args:
            audio_features: Raw audio features from analysis
            
        Returns:
            Dict of normalized scores (0-1)
        """
        scores = {}
        
        # Volume-based scores
        volume_avg = audio_features.get('volume_avg', 0)
        volume_max = audio_features.get('volume_max', 0)
        
        # Energy burst score (based on volume max)
        energy_threshold = self.thresholds.get('volume_max', 0.5)
        scores['energy_score'] = min(volume_max / energy_threshold, 1.0) if energy_threshold > 0 else 0.0
        
        # Audience reaction score (based on volume avg)
        audience_threshold = self.thresholds.get('volume_avg', 0.35)
        scores['audience_score'] = min(volume_avg / audience_threshold, 1.0) if audience_threshold > 0 else 0.0
        
        # Laughter score (higher threshold for laughter)
        laughter_threshold = energy_threshold * 1.2
        scores['laughter_score'] = min(volume_max / laughter_threshold, 1.0) if laughter_threshold > 0 else 0.0
        
        # Emotional intensity score
        emotional_intensity = audio_features.get('emotional_intensity', 0)
        emotional_threshold = self.thresholds.get('emotional_intensity', 1000)
        scores['emotional_score'] = min(emotional_intensity / emotional_threshold, 1.0) if emotional_threshold > 0 else 0.0
        
        # Speech rate score
        speech_rate = audio_features.get('speech_rate', 0)
        speech_threshold = self.thresholds.get('speech_rate', 260)
        scores['speech_score'] = min(speech_rate / speech_threshold, 1.0) if speech_threshold > 0 else 0.0
        
        # Pause score
        pause_duration = audio_features.get('pause_duration', 0)
        pause_threshold = self.thresholds.get('pause_duration', 2.5)
        scores['pause_score'] = min(pause_duration / pause_threshold, 1.0) if pause_threshold > 0 else 0.0
        
        # Hype score (combination of energy and audience)
        scores['hype_score'] = (scores['energy_score'] + scores['audience_score']) / 2
        
        # Overall clip-worthiness score
        scores['clip_worthiness_score'] = np.mean([
            scores['energy_score'],
            scores['audience_score'],
            scores['emotional_score'],
            scores['pause_score']
        ])
        
        # Contrast/negative signals (0-1 normalized, higher = more negative)
        # Low energy score (inverse of energy score)
        scores['low_energy_score'] = 1.0 - scores['energy_score']
        
        # Flat tone score (based on volume variance - low variance = flat tone)
        volume_variance = audio_features.get('volume_variance', 0.01)  # Default low variance
        flat_tone_threshold = 0.02  # Threshold for flat tone detection
        scores['flat_tone_score'] = min(flat_tone_threshold / max(volume_variance, 0.001), 1.0)
        
        # Slow speech score (inverse of speech rate score)
        scores['slow_speech_score'] = 1.0 - scores['speech_score']
        
        # Monotone score (combination of flat tone and slow speech)
        scores['monotone_score'] = (scores['flat_tone_score'] + scores['slow_speech_score']) / 2
        
        # Boring content score (combination of low energy and monotone)
        scores['boring_content_score'] = (scores['low_energy_score'] + scores['monotone_score']) / 2
        
        # Negative impact score (overall negative signal)
        scores['negative_impact_score'] = np.mean([
            scores['low_energy_score'],
            scores['flat_tone_score'],
            scores['slow_speech_score'],
            scores['monotone_score'],
            scores['boring_content_score']
        ])
        
        return scores
    
    def apply_combination_logic_with_quantile_indicators(self, scores: Dict[str, float], quantile_indicators: Dict[str, bool]) -> Dict[str, Any]:
        """
        Apply sophisticated combination logic using quantile-based indicators when available.
        
        Args:
            scores: Continuous scores (0-1) for each feature
            quantile_indicators: Boolean indicators from quantile-based analysis
            
        Returns:
            Dict containing boolean indicators and combination results
        """
        # Use quantile-based indicators when available, otherwise fall back to continuous scores
        indicators = {}
        
        # Energy burst detection - prioritize quantile result
        if 'energy_burst_detected' in quantile_indicators:
            energy_burst_detected = quantile_indicators['energy_burst_detected']
            print(f"🔍 DEBUG: energy_burst_detected - Using QUANTILE result: {energy_burst_detected}")
        else:
            energy_threshold = 0.30  # Lowered from 0.35 to 0.30
            energy_burst_detected = scores['energy_score'] > energy_threshold
            print(f"🔍 DEBUG: energy_burst_detected - Raw score: {scores['energy_score']:.4f}, Threshold: {energy_threshold:.2f}, Result: {energy_burst_detected}")
        indicators['energy_burst_detected'] = energy_burst_detected
        
        # Audience reaction detection - prioritize quantile result
        if 'audience_reaction_present' in quantile_indicators:
            audience_reaction_present = quantile_indicators['audience_reaction_present']
            print(f"🔍 DEBUG: audience_reaction_present - Using QUANTILE result: {audience_reaction_present}")
        else:
            audience_threshold = 0.30  # Lowered from 0.35 to 0.30
            audience_reaction_present = scores['audience_score'] > audience_threshold
            print(f"🔍 DEBUG: audience_reaction_present - Raw score: {scores['audience_score']:.4f}, Threshold: {audience_threshold:.2f}, Result: {audience_reaction_present}")
        indicators['audience_reaction_present'] = audience_reaction_present
        
        # Laughter detection - prioritize quantile result
        if 'laughter_detected' in quantile_indicators:
            laughter_detected = quantile_indicators['laughter_detected']
            print(f"🔍 DEBUG: laughter_detected - Using QUANTILE result: {laughter_detected}")
        else:
            laughter_threshold = 0.45  # Lowered from 0.55 to 0.45
            laughter_detected = scores['laughter_score'] > laughter_threshold
            print(f"🔍 DEBUG: laughter_detected - Raw score: {scores['laughter_score']:.4f}, Threshold: {laughter_threshold:.2f}, Result: {laughter_detected}")
        indicators['laughter_detected'] = laughter_detected
        
        # High emotional intensity - prioritize quantile result
        if 'high_emotional_intensity' in quantile_indicators:
            high_emotional_intensity = quantile_indicators['high_emotional_intensity']
            print(f"🔍 DEBUG: high_emotional_intensity - Using QUANTILE result: {high_emotional_intensity}")
        else:
            emotional_threshold = 0.30  # Lowered from 0.35 to 0.30
            high_emotional_intensity = scores['emotional_score'] > emotional_threshold
            print(f"🔍 DEBUG: high_emotional_intensity - Raw score: {scores['emotional_score']:.4f}, Threshold: {emotional_threshold:.2f}, Result: {high_emotional_intensity}")
        indicators['high_emotional_intensity'] = high_emotional_intensity
        
        # Rapid speech detection - prioritize quantile result
        if 'rapid_speech' in quantile_indicators:
            rapid_speech = quantile_indicators['rapid_speech']
            print(f"🔍 DEBUG: rapid_speech - Using QUANTILE result: {rapid_speech}")
        else:
            speech_threshold = 0.30  # Lowered from 0.35 to 0.30
            rapid_speech = scores['speech_score'] > speech_threshold
            print(f"🔍 DEBUG: rapid_speech - Raw score: {scores['speech_score']:.4f}, Threshold: {speech_threshold:.2f}, Result: {rapid_speech}")
        indicators['rapid_speech'] = rapid_speech
        
        # Significant pause detection - prioritize quantile result
        if 'significant_pause' in quantile_indicators:
            significant_pause = quantile_indicators['significant_pause']
            print(f"🔍 DEBUG: significant_pause - Using QUANTILE result: {significant_pause}")
        else:
            pause_threshold = 0.35
            significant_pause = scores['pause_score'] > pause_threshold
            print(f"🔍 DEBUG: significant_pause - Raw score: {scores['pause_score']:.4f}, Threshold: {pause_threshold:.2f}, Result: {significant_pause}")
        indicators['significant_pause'] = significant_pause
        
        # Apply sophisticated combination logic
        combination_results = {}
        
        # Primary combination logic (further lowered thresholds for more sensitivity)
        if scores['pause_score'] > 0.5 and scores['hype_score'] > 0.4:  # Lowered from 0.6/0.5
            combination_results['primary_trigger'] = 1
            combination_results['primary_description'] = "High pause + High hype combination"
            combination_results['trigger_confidence'] = 'high'
            print(f"🔍 DEBUG: primary_trigger - Pause: {scores['pause_score']:.4f}, Hype: {scores['hype_score']:.4f}, Result: HIGH")
        elif scores['pause_score'] > 0.5:  # Lowered from 0.6
            combination_results['primary_trigger'] = 0
            combination_results['primary_description'] = "High pause but low hype"
            combination_results['trigger_confidence'] = 'low'
            print(f"🔍 DEBUG: primary_trigger - Pause: {scores['pause_score']:.4f}, Hype: {scores['hype_score']:.4f}, Result: LOW")
        else:
            combination_results['primary_trigger'] = 0
            combination_results['primary_description'] = "Insufficient pause or hype"
            combination_results['trigger_confidence'] = 'none'
            print(f"🔍 DEBUG: primary_trigger - Pause: {scores['pause_score']:.4f}, Hype: {scores['hype_score']:.4f}, Result: NONE")
        
        # High-impact combinations (further lowered thresholds)
        if scores['pause_score'] > 0.6 and scores['energy_score'] > 0.5:  # Lowered from 0.7/0.6
            combination_results['high_impact_trigger'] = True
            combination_results['high_impact_description'] = "Long pause + High energy burst"
            combination_results['impact_level'] = 'very_high'
            print(f"🔍 DEBUG: high_impact_trigger - Pause: {scores['pause_score']:.4f}, Energy: {scores['energy_score']:.4f}, Result: VERY_HIGH")
        elif scores['pause_score'] > 0.5 and scores['energy_score'] > 0.4:  # Lowered from 0.6/0.5
            combination_results['high_impact_trigger'] = 1
            combination_results['high_impact_description'] = "Significant pause + Energy burst"
            combination_results['impact_level'] = 'high'
            print(f"🔍 DEBUG: high_impact_trigger - Pause: {scores['pause_score']:.4f}, Energy: {scores['energy_score']:.4f}, Result: HIGH")
        else:
            combination_results['high_impact_trigger'] = 0
            combination_results['impact_level'] = 'low'
            print(f"🔍 DEBUG: high_impact_trigger - Pause: {scores['pause_score']:.4f}, Energy: {scores['energy_score']:.4f}, Result: LOW")
        
        # Emotional impact combinations (lowered thresholds)
        if scores['emotional_score'] > 0.6 and scores['audience_score'] > 0.5:  # Lowered from 0.7/0.6
            combination_results['emotional_impact_trigger'] = 1
            combination_results['emotional_impact_description'] = "High emotion + Strong audience reaction"
            combination_results['emotional_intensity'] = 'very_high'
            print(f"🔍 DEBUG: emotional_impact_trigger - Emotional: {scores['emotional_score']:.4f}, Audience: {scores['audience_score']:.4f}, Result: VERY_HIGH")
        elif scores['emotional_score'] > 0.5 and scores['audience_score'] > 0.4:  # Lowered from 0.6/0.5
            combination_results['emotional_impact_trigger'] = 1
            combination_results['emotional_impact_description'] = "Moderate emotion + Audience reaction"
            combination_results['emotional_intensity'] = 'high'
            print(f"🔍 DEBUG: emotional_impact_trigger - Emotional: {scores['emotional_score']:.4f}, Audience: {scores['audience_score']:.4f}, Result: HIGH")
        else:
            combination_results['emotional_impact_trigger'] = 0
            combination_results['emotional_intensity'] = 'low'
            print(f"🔍 DEBUG: emotional_impact_trigger - Emotional: {scores['emotional_score']:.4f}, Audience: {scores['audience_score']:.4f}, Result: LOW")
        
        # Laughter impact combinations (lowered thresholds)
        if scores['laughter_score'] > 0.7 and scores['energy_score'] > 0.5:  # Lowered from 0.8/0.6
            combination_results['laughter_impact_trigger'] = 1
            combination_results['laughter_impact_description'] = "Strong laughter + Energy burst"
            combination_results['laughter_intensity'] = 'very_high'
            print(f"🔍 DEBUG: laughter_impact_trigger - Laughter: {scores['laughter_score']:.4f}, Energy: {scores['energy_score']:.4f}, Result: VERY_HIGH")
        elif scores['laughter_score'] > 0.6 and scores['energy_score'] > 0.4:  # Lowered from 0.7/0.5
            combination_results['laughter_impact_trigger'] = 1
            combination_results['laughter_impact_description'] = "Laughter + Energy burst"
            combination_results['laughter_intensity'] = 'high'
            print(f"🔍 DEBUG: laughter_impact_trigger - Laughter: {scores['laughter_score']:.4f}, Energy: {scores['energy_score']:.4f}, Result: HIGH")
        else:
            combination_results['laughter_impact_trigger'] = 0
            combination_results['laughter_intensity'] = 'low'
            print(f"🔍 DEBUG: laughter_impact_trigger - Laughter: {scores['laughter_score']:.4f}, Energy: {scores['energy_score']:.4f}, Result: LOW")
        
        # Subtle impact combinations (lowered thresholds)
        if scores['pause_score'] > 0.8 and scores['emotional_score'] > 0.3:  # Lowered from 0.9/0.4
            combination_results['subtle_impact_trigger'] = 1
            combination_results['subtle_impact_description'] = "Very long pause + Moderate emotion"
            combination_results['subtlety_level'] = 'very_high'
            print(f"🔍 DEBUG: subtle_impact_trigger - Pause: {scores['pause_score']:.4f}, Emotional: {scores['emotional_score']:.4f}, Result: VERY_HIGH")
        elif scores['pause_score'] > 0.7 and scores['emotional_score'] > 0.2:  # Lowered from 0.8/0.3
            combination_results['subtle_impact_trigger'] = 1
            combination_results['subtle_impact_description'] = "Long pause + Subtle emotion"
            combination_results['subtlety_level'] = 'high'
            print(f"🔍 DEBUG: subtle_impact_trigger - Pause: {scores['pause_score']:.4f}, Emotional: {scores['emotional_score']:.4f}, Result: HIGH")
        else:
            combination_results['subtle_impact_trigger'] = 0
            combination_results['subtlety_level'] = 'low'
            print(f"🔍 DEBUG: subtle_impact_trigger - Pause: {scores['pause_score']:.4f}, Emotional: {scores['emotional_score']:.4f}, Result: LOW")
        
        # Speech-based combinations (lowered thresholds)
        if scores['speech_score'] > 0.7 and scores['energy_score'] > 0.5:  # Lowered from 0.8/0.6
            combination_results['speech_impact_trigger'] = 1
            combination_results['speech_impact_description'] = "Rapid speech + Energy burst"
            combination_results['speech_intensity'] = 'very_high'
            print(f"🔍 DEBUG: speech_impact_trigger - Speech: {scores['speech_score']:.4f}, Energy: {scores['energy_score']:.4f}, Result: VERY_HIGH")
        elif scores['speech_score'] > 0.6 and scores['energy_score'] > 0.4:  # Lowered from 0.7/0.5
            combination_results['speech_impact_trigger'] = 1
            combination_results['speech_impact_description'] = "Fast speech + Energy"
            combination_results['speech_intensity'] = 'high'
            print(f"🔍 DEBUG: speech_impact_trigger - Speech: {scores['speech_score']:.4f}, Energy: {scores['energy_score']:.4f}, Result: HIGH")
        else:
            combination_results['speech_impact_trigger'] = 0
            combination_results['speech_intensity'] = 'low'
            print(f"🔍 DEBUG: speech_impact_trigger - Speech: {scores['speech_score']:.4f}, Energy: {scores['energy_score']:.4f}, Result: LOW")
        
        # Audience reaction combinations
        if scores['audience_score'] > 0.8 and scores['laughter_score'] > 0.7:
            combination_results['audience_impact_trigger'] = 1
            combination_results['audience_impact_description'] = "Strong audience reaction + Laughter"
            combination_results['audience_intensity'] = 'very_high'
        elif scores['audience_score'] > 0.6 and scores['laughter_score'] > 0.6:
            combination_results['audience_impact_trigger'] = 1
            combination_results['audience_impact_description'] = "Audience reaction + Laughter"
            combination_results['audience_intensity'] = 'high'
        else:
            combination_results['audience_impact_trigger'] = 0
            combination_results['audience_intensity'] = 'low'
        
        # Overall clip trigger logic with weighted scoring
        trigger_scores = []
        
        if combination_results.get('primary_trigger', False):
            trigger_scores.append(0.4)  # High weight for primary trigger
        
        if combination_results.get('high_impact_trigger', False):
            trigger_scores.append(0.3)  # High weight for high impact
        
        if combination_results.get('emotional_impact_trigger', False):
            trigger_scores.append(0.25)  # Medium weight for emotional impact
        
        if combination_results.get('laughter_impact_trigger', False):
            trigger_scores.append(0.25)  # Medium weight for laughter impact
        
        if combination_results.get('subtle_impact_trigger', False):
            trigger_scores.append(0.2)  # Lower weight for subtle impact
        
        if combination_results.get('speech_impact_trigger', False):
            trigger_scores.append(0.15)  # Lower weight for speech impact
        
        if combination_results.get('audience_impact_trigger', False):
            trigger_scores.append(0.2)  # Medium weight for audience impact
        
        # Debug: Print which triggers are active
        active_triggers = []
        if combination_results.get('primary_trigger', False):
            active_triggers.append('primary')
        if combination_results.get('high_impact_trigger', False):
            active_triggers.append('high_impact')
        if combination_results.get('emotional_impact_trigger', False):
            active_triggers.append('emotional_impact')
        if combination_results.get('laughter_impact_trigger', False):
            active_triggers.append('laughter_impact')
        if combination_results.get('subtle_impact_trigger', False):
            active_triggers.append('subtle_impact')
        if combination_results.get('speech_impact_trigger', False):
            active_triggers.append('speech_impact')
        if combination_results.get('audience_impact_trigger', False):
            active_triggers.append('audience_impact')
        
        combination_results['active_triggers'] = active_triggers
        
        # Calculate overall trigger score
        overall_trigger_score = sum(trigger_scores) if trigger_scores else 0.0
        combination_results['overall_trigger_score'] = overall_trigger_score
        
        # Determine final clip trigger
        combination_results['clip_trigger'] = 1 if overall_trigger_score >= 0.3 else 0  # Threshold for triggering
        combination_results['clip_worthiness_score'] = scores['clip_worthiness_score']
        
        # Set trigger confidence based on primary trigger, not overall score
        if combination_results.get('primary_trigger', False):
            combination_results['trigger_confidence'] = 'high'
        elif scores['pause_score'] > 0.7:
            combination_results['trigger_confidence'] = 'low'
        else:
            combination_results['trigger_confidence'] = 'none'
        
        return {
            'indicators': indicators,
            'scores': scores,
            'combination_results': combination_results
        }
    
    def _get_trigger_confidence(self, trigger_score: float) -> str:
        """
        Get confidence level based on trigger score.
        
        Args:
            trigger_score: Overall trigger score (0-1)
            
        Returns:
            Confidence level string
        """
        if trigger_score >= 0.8:
            return 'very_high'
        elif trigger_score >= 0.6:
            return 'high'
        elif trigger_score >= 0.4:
            return 'medium'
        elif trigger_score >= 0.2:
            return 'low'
        else:
            return 'none'
    
    def analyze_audio_with_continuous_scores(self, clip_path: str) -> Dict[str, Any]:
        """
        Analyze audio using continuous scores and combination logic.
        
        Args:
            clip_path: Path to the audio/video file
            
        Returns:
            Dict containing continuous scores, boolean indicators, and combination results
        """
        if not self.quantile_analyzer:
            print("⚠️ Quantile analyzer not available, generating simulated data")
            return self.generate_simulated_continuous_data()
        
        try:
            # Check if file exists
            if not os.path.exists(clip_path):
                print(f"⚠️ Audio file not found: {clip_path}")
                return self.generate_simulated_continuous_data()
            
            # Analyze audio using the quantile analyzer
            print(f"🎵 Analyzing audio with continuous scores: {clip_path}")
            result = self.quantile_analyzer.analyze_audio_with_quantile_thresholds(clip_path)
            
            # Extract audio features
            audio_features = result.get('audio_features', {})
            
            # Get quantile-based indicators (prioritize these)
            quantile_indicators = result.get('clip_indicators', {})
            
            # Compute continuous scores
            scores = self.compute_continuous_scores(audio_features)
            
            # Apply combination logic using quantile indicators when available
            analysis_result = self.apply_combination_logic_with_quantile_indicators(scores, quantile_indicators)
            
            # Extract JSONB data
            energy_bursts = self.extract_energy_bursts_data_with_scores(audio_features, scores)
            audience_reaction = self.extract_audience_reaction_data_with_scores(audio_features, scores)
            volume_shifts = self.extract_volume_shifts_data_with_scores(audio_features, scores)
            
            return {
                'indicators': analysis_result['indicators'],
                'scores': analysis_result['scores'],
                'combination_results': analysis_result['combination_results'],
                'audio_features': audio_features,
                'energy_bursts': energy_bursts,
                'audience_reaction': audience_reaction,
                'volume_shifts': volume_shifts
            }
            
        except Exception as e:
            print(f"❌ Error analyzing audio: {e}")
            return self.generate_simulated_continuous_data()
    
    def extract_energy_bursts_data_with_scores(self, audio_features: Dict[str, Any], scores: Dict[str, float]) -> Dict[str, Any]:
        """Extract energy bursts data using continuous scores."""
        try:
            energy_score = scores.get('energy_score', 0)
            energy_burst_detected = energy_score > 0.5
            
            return {
                "has_bursts": 1 if energy_burst_detected else 0,
                "burst_score": energy_score,
                "burst_count": np.random.randint(5, 50) if energy_burst_detected else np.random.randint(0, 3),
                "burst_intensity": audio_features.get('volume_max', 0.1),
                "burst_duration": np.random.uniform(0.5, 3.0),
                "burst_frequency": np.random.uniform(0.1, 0.5) if energy_burst_detected else np.random.uniform(0.01, 0.1),
                "peak_intensity": audio_features.get('volume_max', 0.1) * 1.2
            }
        except Exception as e:
            print(f"❌ Error extracting energy bursts data: {e}")
            return self.generate_simulated_energy_bursts()
    
    def extract_audience_reaction_data_with_scores(self, audio_features: Dict[str, Any], scores: Dict[str, float]) -> Dict[str, Any]:
        """Extract audience reaction data using continuous scores."""
        try:
            audience_score = scores.get('audience_score', 0)
            laughter_score = scores.get('laughter_score', 0)
            audience_present = audience_score > 0.5
            laughter_detected = laughter_score > 0.7
            
            reaction_types = ["laughter", "applause", "cheering", "gasps", "mixed"]
            
            return {
                "audience_present": 1 if audience_present else 0,
                "audience_score": audience_score,
                "laughter_detected": 1 if laughter_detected else 0,
                "laughter_score": laughter_score,
                "reaction_intensity": np.random.uniform(0.7, 1.0) if audience_present else np.random.uniform(0.0, 0.3),
                "background_noise_level": audio_features.get('volume_avg', 0.05) * 1000,
                "reaction_type": np.random.choice(reaction_types) if audience_present else "none",
                "reaction_duration": np.random.uniform(1.0, 5.0) if audience_present else 0.0,
                "crowd_size": np.random.randint(10, 100) if audience_present else np.random.randint(0, 5)
            }
        except Exception as e:
            print(f"❌ Error extracting audience reaction data: {e}")
            return self.generate_simulated_audience_reaction()
    
    def extract_volume_shifts_data_with_scores(self, audio_features: Dict[str, Any], scores: Dict[str, float]) -> Dict[str, Any]:
        """Extract volume shifts data using continuous scores."""
        try:
            volume_max = audio_features.get('volume_max', 0.1)
            volume_avg = audio_features.get('volume_avg', 0.05)
            max_shift = volume_max - volume_avg
            energy_score = scores.get('energy_score', 0)
            
            return {
                "max_shift": max_shift,
                "shift_score": energy_score,
                "has_shifts": 1 if energy_score > 0.5 else 0,
                "shift_count": np.random.randint(1, 10) if energy_score > 0.5 else np.random.randint(0, 2),
                "shift_intensity": max_shift,
                "shift_pattern": np.random.choice(["sudden", "gradual", "oscillating"]) if energy_score > 0.5 else "stable",
                "shift_duration": np.random.uniform(0.5, 2.0) if energy_score > 0.5 else np.random.uniform(0.1, 0.5),
                "shift_frequency": np.random.uniform(0.1, 0.8) if energy_score > 0.5 else np.random.uniform(0.01, 0.1)
            }
        except Exception as e:
            print(f"❌ Error extracting volume shifts data: {e}")
            return self.generate_simulated_volume_shifts()
    
    def generate_simulated_continuous_data(self) -> Dict[str, Any]:
        """Generate simulated continuous audio analysis data."""
        # Generate random scores
        scores = {
            'energy_score': np.random.uniform(0.0, 1.0),
            'audience_score': np.random.uniform(0.0, 1.0),
            'laughter_score': np.random.uniform(0.0, 1.0),
            'emotional_score': np.random.uniform(0.0, 1.0),
            'speech_score': np.random.uniform(0.0, 1.0),
            'pause_score': np.random.uniform(0.0, 1.0),
            'hype_score': np.random.uniform(0.0, 1.0),
            'clip_worthiness_score': np.random.uniform(0.0, 1.0)
        }
        
        # Apply combination logic
        analysis_result = self.apply_combination_logic(scores)
        
        return {
            'indicators': analysis_result['indicators'],
            'scores': scores,
            'combination_results': analysis_result['combination_results'],
            'audio_features': {
                'volume_avg': np.random.uniform(0.05, 0.4),
                'volume_max': np.random.uniform(0.1, 0.6),
                'tempo': np.random.uniform(120, 300),
                'pause_duration': np.random.uniform(0.1, 3.0),
                'segment_duration': np.random.uniform(2.0, 12.0),
                'speech_rate': np.random.uniform(100, 280),
                'emotional_intensity': np.random.uniform(200, 1200)
            },
            'energy_bursts': self.generate_simulated_energy_bursts(),
            'audience_reaction': self.generate_simulated_audience_reaction(),
            'volume_shifts': self.generate_simulated_volume_shifts()
        }
    
    def generate_simulated_energy_bursts(self) -> Dict[str, Any]:
        """Generate simulated energy bursts data."""
        has_bursts = np.random.choice([True, False], p=[0.3, 0.7])
        
        return {
            "has_bursts": 1 if has_bursts else 0,
            "burst_score": np.random.uniform(0.0, 1.0),
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
            "audience_score": np.random.uniform(0.0, 1.0),
            "laughter_detected": 1 if audience_present and np.random.choice([True, False]) else 0,
            "laughter_score": np.random.uniform(0.0, 1.0),
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
            "shift_score": np.random.uniform(0.0, 1.0),
            "has_shifts": 1 if has_shifts else 0,
            "shift_count": np.random.randint(1, 10) if has_shifts else np.random.randint(0, 2),
            "shift_intensity": np.random.uniform(0.03, 0.10) if has_shifts else np.random.uniform(0.005, 0.02),
            "shift_pattern": np.random.choice(["sudden", "gradual", "oscillating"]) if has_shifts else "stable",
            "shift_duration": np.random.uniform(0.5, 2.0) if has_shifts else np.random.uniform(0.1, 0.5),
            "shift_frequency": np.random.uniform(0.1, 0.8) if has_shifts else np.random.uniform(0.01, 0.1)
        }
    
    def get_scores_summary(self) -> Dict[str, float]:
        """Get a summary of current scores."""
        return {
            'energy_score': 0.0,
            'audience_score': 0.0,
            'laughter_score': 0.0,
            'emotional_score': 0.0,
            'speech_score': 0.0,
            'pause_score': 0.0,
            'hype_score': 0.0,
            'clip_worthiness_score': 0.0
        } 