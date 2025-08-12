#!/usr/bin/env python3
"""
Context Window Predictor
Uses sliding windows of 3 segments to capture temporal relationships
"""

import os
import sys
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from supabase import create_client
from dotenv import load_dotenv
import openai
from sklearn.linear_model import LogisticRegression
import joblib

# Add src to path
sys.path.append(str(Path(__file__).parent))

from audio_analysis import analyze_clip_audio
from supabase_utils import get_model_from_registry

# Load environment variables
load_dotenv()

class ContextWindowPredictor:
    """
    Predicts clip-worthiness using context windows of 3 segments
    Captures temporal relationships like setup->punchline, action->reaction
    """
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not all([self.supabase_url, self.supabase_key, self.openai_api_key]):
            raise ValueError("Missing required environment variables")
        
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
        
        # Load the trained model
        self.model = self._load_model()
        
    def _load_model(self) -> LogisticRegression:
        """Load the trained model from registry"""
        try:
            model_data = get_model_from_registry()
            if model_data and 'model_data' in model_data:
                model = joblib.loads(model_data['model_data'])
                print(f"✅ Loaded context window model: {model_data.get('model_version', 'unknown')}")
                return model
            else:
                raise ValueError("No model found in registry")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get OpenAI embedding for text"""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ Error getting embedding: {e}")
            raise
    
    def _create_context_window(self, segments: List[Dict]) -> List[Dict]:
        """
        Create context windows from segments
        Each window contains [segment_t-1, segment_t, segment_t+1]
        """
        context_windows = []
        
        for i in range(len(segments)):
            # Get previous, current, and next segments
            prev_segment = segments[i-1] if i > 0 else {"transcript": "", "audio_features": {}}
            current_segment = segments[i]
            next_segment = segments[i+1] if i < len(segments)-1 else {"transcript": "", "audio_features": {}}
            
            # Create context window
            context_window = {
                "window_id": f"window_{i}",
                "prev_segment": prev_segment,
                "current_segment": current_segment,
                "next_segment": next_segment,
                "combined_transcript": f"{prev_segment.get('transcript', '')} {current_segment.get('transcript', '')} {next_segment.get('transcript', '')}".strip(),
                "temporal_features": self._extract_temporal_features(prev_segment, current_segment, next_segment)
            }
            
            context_windows.append(context_window)
        
        return context_windows
    
    def _extract_temporal_features(self, prev: Dict, current: Dict, next: Dict) -> Dict:
        """
        Extract temporal features that capture relationships between segments
        """
        features = {}
        
        # Volume dynamics across segments
        prev_vol = prev.get('audio_features', {}).get('volume_avg', 0)
        curr_vol = current.get('audio_features', {}).get('volume_avg', 0)
        next_vol = next.get('audio_features', {}).get('volume_avg', 0)
        
        features['volume_increase'] = curr_vol > prev_vol
        features['volume_decrease'] = curr_vol < prev_vol
        features['volume_spike'] = curr_vol > (prev_vol + next_vol) / 2
        features['volume_drop'] = curr_vol < (prev_vol + next_vol) / 2
        
        # Emotional intensity patterns
        prev_emotion = prev.get('audio_features', {}).get('emotional_intensity', 0)
        curr_emotion = current.get('audio_features', {}).get('emotional_intensity', 0)
        next_emotion = next.get('audio_features', {}).get('emotional_intensity', 0)
        
        features['emotion_build_up'] = prev_emotion < curr_emotion < next_emotion
        features['emotion_peak'] = curr_emotion > prev_emotion and curr_emotion > next_emotion
        features['emotion_release'] = prev_emotion > curr_emotion > next_emotion
        
        # Speech rate patterns
        prev_speech = prev.get('audio_features', {}).get('speech_rate', 0)
        curr_speech = current.get('audio_features', {}).get('speech_rate', 0)
        next_speech = next.get('audio_features', {}).get('speech_rate', 0)
        
        features['speech_acceleration'] = prev_speech < curr_speech < next_speech
        features['speech_deceleration'] = prev_speech > curr_speech > next_speech
        features['speech_pause'] = curr_speech < (prev_speech + next_speech) / 2
        
        # Temporal indicators
        features['setup_to_punchline'] = (
            prev.get('audio_features', {}).get('emotional_intensity', 0) < 300 and
            curr.get('audio_features', {}).get('emotional_intensity', 0) > 500 and
            'laughter' in str(current.get('audio_features', {}).get('laughter_detected', False)).lower()
        )
        
        features['action_to_reaction'] = (
            prev.get('audio_features', {}).get('volume_max', 0) < 0.3 and
            curr.get('audio_features', {}).get('volume_max', 0) > 0.6 and
            curr.get('audio_features', {}).get('audience_reaction_present', False)
        )
        
        features['mistake_to_recovery'] = (
            prev.get('audio_features', {}).get('emotional_intensity', 0) > 400 and
            curr.get('audio_features', {}).get('emotional_intensity', 0) < 200 and
            next.get('audio_features', {}).get('emotional_intensity', 0) > 300
        )
        
        return features
    
    def _get_context_embedding(self, context_window: Dict) -> List[float]:
        """Get embedding for the combined context window"""
        combined_text = context_window['combined_transcript']
        return self._get_embedding(combined_text)
    
    def _enhance_embedding_with_temporal_features(self, embedding: List[float], temporal_features: Dict) -> List[float]:
        """
        Enhance the text embedding with temporal features
        Converts boolean features to numerical and appends to embedding
        """
        # Convert boolean features to numerical
        temporal_numerical = []
        for key, value in temporal_features.items():
            if isinstance(value, bool):
                temporal_numerical.append(1.0 if value else 0.0)
            elif isinstance(value, (int, float)):
                temporal_numerical.append(float(value))
            else:
                temporal_numerical.append(0.0)
        
        # Normalize temporal features to match embedding scale
        if temporal_numerical:
            temporal_numerical = np.array(temporal_numerical)
            temporal_numerical = (temporal_numerical - np.mean(temporal_numerical)) / (np.std(temporal_numerical) + 1e-8)
            temporal_numerical = temporal_numerical.tolist()
        
        # Combine text embedding with temporal features
        enhanced_embedding = embedding + temporal_numerical
        return enhanced_embedding
    
    def predict_context_window(self, segments: List[Dict]) -> List[Dict]:
        """
        Predict clip-worthiness for each context window
        Returns predictions with temporal context
        """
        if len(segments) < 1:
            return []
        
        # Create context windows
        context_windows = self._create_context_window(segments)
        predictions = []
        
        for window in context_windows:
            try:
                # Get base embedding
                base_embedding = self._get_context_embedding(window)
                
                # Enhance with temporal features
                enhanced_embedding = self._enhance_embedding_with_temporal_features(
                    base_embedding, 
                    window['temporal_features']
                )
                
                # Make prediction
                prediction_score = self.model.predict_proba([enhanced_embedding])[0][1]
                is_worthy = prediction_score > 0.5
                
                # Analyze temporal patterns
                temporal_analysis = self._analyze_temporal_patterns(window)
                
                prediction = {
                    "window_id": window['window_id'],
                    "prediction_score": prediction_score,
                    "is_worthy": is_worthy,
                    "temporal_features": window['temporal_features'],
                    "temporal_analysis": temporal_analysis,
                    "context_summary": self._summarize_context(window)
                }
                
                predictions.append(prediction)
                
            except Exception as e:
                print(f"❌ Error predicting context window {window['window_id']}: {e}")
                continue
        
        return predictions
    
    def _analyze_temporal_patterns(self, window: Dict) -> Dict:
        """Analyze temporal patterns in the context window"""
        features = window['temporal_features']
        
        patterns = {
            "setup_punchline": features.get('setup_to_punchline', False),
            "action_reaction": features.get('action_to_reaction', False),
            "mistake_recovery": features.get('mistake_to_recovery', False),
            "volume_dynamics": features.get('volume_spike', False) or features.get('volume_drop', False),
            "emotional_arc": features.get('emotion_build_up', False) or features.get('emotion_peak', False),
            "speech_patterns": features.get('speech_acceleration', False) or features.get('speech_pause', False)
        }
        
        return patterns
    
    def _summarize_context(self, window: Dict) -> str:
        """Summarize the context window for logging"""
        prev_text = window['prev_segment'].get('transcript', '')[:50]
        curr_text = window['current_segment'].get('transcript', '')[:50]
        next_text = window['next_segment'].get('transcript', '')[:50]
        
        return f"Prev: '{prev_text}...' → Curr: '{curr_text}...' → Next: '{next_text}...'"
    
    def log_context_predictions(self, clip_id: str, predictions: List[Dict]) -> None:
        """Log context window predictions to Supabase"""
        try:
            for pred in predictions:
                prediction_data = {
                    "clip_id": clip_id,
                    "window_id": pred['window_id'],
                    "prediction_score": pred['prediction_score'],
                    "is_worthy": pred['is_worthy'],
                    "temporal_features": json.dumps(pred['temporal_features']),
                    "temporal_analysis": json.dumps(pred['temporal_analysis']),
                    "context_summary": pred['context_summary'],
                    "prediction_type": "context_window"
                }
                
                self.supabase.table("clip_predictions").insert(prediction_data).execute()
                print(f"✅ Logged context prediction: {pred['window_id']} - Score: {pred['prediction_score']:.3f}")
                
        except Exception as e:
            print(f"❌ Error logging context predictions: {e}")

def is_clip_worthy_with_context(segments: List[Dict], clip_id: str = None) -> Tuple[bool, List[Dict]]:
    """
    Main function to predict clip-worthiness using context windows
    
    Args:
        segments: List of segments with transcript and audio features
        clip_id: Optional clip ID for logging
    
    Returns:
        Tuple of (is_worthy, detailed_predictions)
    """
    try:
        predictor = ContextWindowPredictor()
        predictions = predictor.predict_context_window(segments)
        
        if not predictions:
            return False, []
        
        # Determine overall clip-worthiness
        # Consider both individual scores and temporal patterns
        avg_score = np.mean([p['prediction_score'] for p in predictions])
        high_scoring_windows = [p for p in predictions if p['prediction_score'] > 0.7]
        temporal_patterns = [p for p in predictions if any(p['temporal_analysis'].values())]
        
        # Clip is worthy if:
        # 1. Average score is high, OR
        # 2. Has high-scoring windows, OR  
        # 3. Has strong temporal patterns
        is_worthy = (
            avg_score > 0.6 or
            len(high_scoring_windows) > 0 or
            len(temporal_patterns) > 0
        )
        
        # Log predictions if clip_id provided
        if clip_id:
            predictor.log_context_predictions(clip_id, predictions)
        
        return is_worthy, predictions
        
    except Exception as e:
        print(f"❌ Error in context window prediction: {e}")
        return False, []

# Test function
def test_context_window_prediction():
    """Test the context window prediction system"""
    print("🧪 Testing Context Window Prediction")
    print("=" * 50)
    
    # Create sample segments
    segments = [
        {
            "transcript": "So I was walking down the street...",
            "audio_features": {
                "volume_avg": 0.1,
                "emotional_intensity": 200,
                "speech_rate": 2.0
            }
        },
        {
            "transcript": "And then this guy comes up to me and says...",
            "audio_features": {
                "volume_avg": 0.3,
                "emotional_intensity": 400,
                "speech_rate": 3.0
            }
        },
        {
            "transcript": "Your fly is down!",
            "audio_features": {
                "volume_avg": 0.8,
                "emotional_intensity": 600,
                "laughter_detected": True,
                "audience_reaction_present": True,
                "speech_rate": 4.0
            }
        }
    ]
    
    try:
        is_worthy, predictions = is_clip_worthy_with_context(segments, "test_clip_123")
        
        print(f"🎯 Overall Prediction: {'WORTHY' if is_worthy else 'NOT WORTHY'}")
        print(f"📊 Number of context windows: {len(predictions)}")
        
        for i, pred in enumerate(predictions):
            print(f"\n🔍 Window {i+1}:")
            print(f"   Score: {pred['prediction_score']:.3f}")
            print(f"   Worthy: {pred['is_worthy']}")
            print(f"   Context: {pred['context_summary']}")
            
            temporal_analysis = pred['temporal_analysis']
            if any(temporal_analysis.values()):
                print("   🎭 Temporal Patterns:")
                for pattern, detected in temporal_analysis.items():
                    if detected:
                        print(f"      ✅ {pattern}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_context_window_prediction() 