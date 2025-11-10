#!/usr/bin/env python3
"""
Prediction script for Self Training Clipping Model.
Provides is_clip_worthy_by_model function to predict clip-worthiness from transcript text.
"""

import joblib
import numpy as np
import openai
import os
import datetime
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any, Tuple

# Load environment variables
load_dotenv()

MODEL_DIR = os.getenv("MODEL_DIR", "models/")

def log_prediction(transcript, score):
    """Log prediction to local file"""
    with open("clip_classifier_log.txt", "a", encoding="utf-8") as f:
        timestamp = datetime.datetime.now().isoformat()
        snippet = transcript[:100].replace("\n", " ")
        f.write(f"[{timestamp}] Score: {score:.2f} | Snippet: {snippet}\n")

def log_prediction_to_supabase(clip_id, transcript, score, triggered, model_version="v1.0"):
    """Log prediction to Supabase clip_predictions table"""
    try:
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        # Prioritize service role key for better permissions
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            print("⚠️ Supabase credentials not found, skipping database logging")
            return False
        
        # Create Supabase client
        supabase = create_client(supabase_url, supabase_key)
        
        # Prepare prediction data
        prediction_data = {
            "clip_id": clip_id,
            "text": transcript,
            "score": float(score),
            "triggered": bool(triggered),  # Ensure boolean type
            "clipworthy": bool(triggered),  # Add clipworthy column (same as triggered)
            "model_version": model_version
        }
        
        # Insert into clip_predictions table
        response = supabase.table("clip_predictions").insert(prediction_data).execute()
        
        if response.data:
            print(f"✅ Prediction logged to Supabase: clip_id={clip_id}, score={score:.3f}, triggered={triggered}")
            return True
        else:
            print("❌ Failed to log prediction to Supabase")
            return False
            
    except Exception as e:
        print(f"❌ Error logging prediction to Supabase: {e}")
        return False

def is_clip_worthy_by_model_with_score(transcript_text, clip_id=None, model_version=None):
    """
    Predict whether a clip is worthy based on its transcript text and return the confidence score.
    
    Args:
        transcript_text: The full transcript string to evaluate
        clip_id: Optional clip ID for logging (if None, will use timestamp)
        model_version: Version of the model being used (if None, will use latest from registry)
        
    Returns:
        Tuple[bool, float]: (is_clip_worthy, confidence_score)
    """
    # Generate clip_id if not provided (for realtime/simulation use)
    if clip_id is None:
        clip_id = f"pred_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    else:
        # Ensure we're using the actual Twitch clip ID when provided
        print(f"📋 Using provided clip ID: {clip_id}")
    
    # 1. Load the trained classifier from model registry or fallback to local file
    classifier = None
    actual_model_version = model_version
    
    try:
        # Try to get model from registry first
        if model_version is None:
            # Get latest model from registry
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
            
            if supabase_url and supabase_key:
                supabase = create_client(supabase_url, supabase_key)
                response = supabase.table("model_registry").select("*").order("created_at", desc=True).limit(1).execute()
                
                if response.data:
                    latest_model = response.data[0]
                    model_path = latest_model.get("file_path")
                    actual_model_version = latest_model.get("version", "v1.0")
                    
                    if model_path and os.path.exists(model_path):
                        classifier = joblib.load(model_path)
                        print(f"✅ Loaded model from registry: {actual_model_version}")
                    else:
                        print(f"⚠️  Model file not found: {model_path}, falling back to local file")
                else:
                    print("⚠️  No models in registry, falling back to local file")
        
        # Fallback to local file if registry failed
        if classifier is None:
            classifier = joblib.load(Path(MODEL_DIR) / "clip_classifier.pkl")
            actual_model_version = actual_model_version or "v1.0"
            print(f"✅ Loaded model from local file: {actual_model_version}")
            
    except Exception as e:
        print(f"❌ Error loading model from registry: {e}")
        # Final fallback to local file
        try:
            classifier = joblib.load(Path(MODEL_DIR) / "clip_classifier.pkl")
            actual_model_version = actual_model_version or "v1.0"
            print(f"✅ Loaded model from local file (fallback): {actual_model_version}")
        except Exception as e2:
            print(f"❌ Failed to load model: {e2}")
            return False, 0.0
    
    # 2. Set up OpenAI API key from environment variable
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required. Please set it before running this script.")
    
    # 3. Convert the transcript into an embedding using OpenAI
    try:
        response = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=transcript_text
        )
        embedding = np.array([response.data[0].embedding])
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return False, 0.0
    
    # 4. Pass the embedding to the classifier's .predict() method
    prediction = classifier.predict(embedding)[0]
    
    # 5. Get probability scores for logging
    prob = classifier.predict_proba(embedding)[0][1]  # Probability of class 1 (clip-worthy)
    
    # 6. Determine if clip is triggered (worthy)
    triggered = prediction == 1
    
    # 7. Log the prediction to local file
    log_prediction(transcript_text, prob)
    
    # 8. Log the prediction to Supabase
    log_prediction_to_supabase(clip_id, transcript_text, prob, triggered, actual_model_version)
    
    # 9. Return both the boolean and the confidence score
    return triggered, prob

def is_clip_worthy_by_model(transcript_text, clip_id=None, model_version=None):
    """
    Predict whether a clip is worthy based on its transcript text.
    
    Args:
        transcript_text: The full transcript string to evaluate
        clip_id: Optional clip ID for logging (if None, will use timestamp)
        model_version: Version of the model being used (if None, will use latest from registry)
        
    Returns:
        True if the clip is predicted to be worthy (label 1), False otherwise
    """
    # Generate clip_id if not provided (for realtime/simulation use)
    if clip_id is None:
        clip_id = f"pred_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    else:
        # Ensure we're using the actual Twitch clip ID when provided
        print(f"📋 Using provided clip ID: {clip_id}")
    
    # 1. Load the trained classifier from model registry or fallback to local file
    classifier = None
    actual_model_version = model_version
    
    try:
        # Try to get model from registry first
        if model_version is None:
            # Get latest model from registry
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
            
            if supabase_url and supabase_key:
                supabase = create_client(supabase_url, supabase_key)
                response = supabase.table("model_registry").select("*").order("created_at", desc=True).limit(1).execute()
                
                if response.data:
                    latest_model = response.data[0]
                    model_path = latest_model.get("file_path")
                    actual_model_version = latest_model.get("version", "v1.0")
                    
                    if model_path and os.path.exists(model_path):
                        classifier = joblib.load(model_path)
                        print(f"✅ Loaded model from registry: {actual_model_version}")
                    else:
                        print(f"⚠️  Model file not found: {model_path}, falling back to local file")
                else:
                    print("⚠️  No models in registry, falling back to local file")
        
        # Fallback to local file if registry failed
        if classifier is None:
            classifier = joblib.load(Path(MODEL_DIR) / "clip_classifier.pkl")
            actual_model_version = actual_model_version or "v1.0"
            print(f"✅ Loaded model from local file: {actual_model_version}")
            
    except Exception as e:
        print(f"❌ Error loading model from registry: {e}")
        # Final fallback to local file
        try:
            classifier = joblib.load(Path(MODEL_DIR) / "clip_classifier.pkl")
            actual_model_version = actual_model_version or "v1.0"
            print(f"✅ Loaded model from local file (fallback): {actual_model_version}")
        except Exception as e2:
            print(f"❌ Failed to load model: {e2}")
            return False
    
    # 2. Set up OpenAI API key from environment variable
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required. Please set it before running this script.")
    
    # 3. Convert the transcript into an embedding using OpenAI
    try:
        response = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=transcript_text
        )
        embedding = np.array([response.data[0].embedding])
    except Exception as e:
        print(f"❌ Error generating embedding: {e}")
        return False
    
    # 4. Pass the embedding to the classifier's .predict() method
    prediction = classifier.predict(embedding)[0]
    
    # 5. Get probability scores for logging
    prob = classifier.predict_proba(embedding)[0][1]  # Probability of class 1 (clip-worthy)
    
    # 6. Determine if clip is triggered (worthy)
    triggered = prediction == 1
    
    # 7. Log the prediction to local file
    log_prediction(transcript_text, prob)
    
    # 8. Log the prediction to Supabase
    log_prediction_to_supabase(clip_id, transcript_text, prob, triggered, actual_model_version)
    
    # 9. Return True if the prediction is 1 (clip-worthy), else return False
    return triggered

def predict_emotion_label(transcript_text: str) -> str:
    """
    Predict emotion label from transcript text using rule-based approach.
    
    Args:
        transcript_text: Text transcript to analyze
        
    Returns:
        str: Predicted emotion label from emotion_labels.txt
    """
    if not transcript_text or len(transcript_text.strip()) == 0:
        return "confusion"  # Default for empty text
    
    text_lower = transcript_text.lower()
    
    # Emotion-specific text indicators (from calculate_emotion_confidence.py)
    emotion_indicators = {
        'excitement': ['wow', 'amazing', 'incredible', 'hype', 'pumped', 'excited', 'let\'s go', 'awesome', 'incredible'],
        'humor': ['haha', 'lol', 'funny', 'joke', 'hilarious', 'comedy', 'laugh', 'lmao', 'rofl', 'haha'],
        'surprise': ['what', 'how', 'omg', 'unbelievable', 'no way', 'impossible', 'holy', 'wow'],
        'awe': ['wow', 'amazing', 'incredible', 'unbelievable', 'perfect', 'insane', 'impossible'],
        'tension': ['oh no', 'careful', 'watch out', 'close', 'almost', 'nervous', 'stress'],
        'frustration': ['ugh', 'damn', 'fuck', 'angry', 'frustrated', 'rage', 'hate', 'terrible'],
        'satisfaction': ['yes', 'finally', 'success', 'victory', 'win', 'achieved', 'perfect'],
        'confusion': ['what', 'huh', 'confused', 'puzzled', 'why', 'how', 'wait', 'what just happened'],
        'nostalgia': ['remember', 'back then', 'old days', 'throwback', 'nostalgic', 'used to'],
        'pride': ['best', 'greatest', 'proud', 'achievement', 'accomplished', 'top'],
        'embarrassment': ['oops', 'sorry', 'mistake', 'embarrassed', 'awkward', 'fail'],
        'relief': ['phew', 'finally', 'escaped', 'close call', 'narrow', 'barely'],
        'disappointment': ['oh no', 'failed', 'missed', 'disappointed', 'sad', 'lost'],
        'curiosity': ['what if', 'interesting', 'curious', 'mystery', 'wonder', 'intriguing'],
        'anticipation': ['wait', 'coming', 'about to', 'get ready', 'prepare', 'soon'],
        'clutch': ['last second', 'game winner', 'clutch', 'final', 'victory', 'clutch play'],
        'rage': ['fuck', 'angry', 'rage', 'furious', 'mad', 'hate', 'terrible'],
        'hype': ['hype', 'pumped', 'excited', 'let\'s go', 'awesome', 'incredible'],
        'tilt': ['tilt', 'frustrated', 'angry', 'rage', 'mad', 'tilted'],
        'flow': ['perfect', 'smooth', 'flow', 'in the zone', 'unstoppable', 'perfect']
    }
    
    # Score each emotion based on indicator matches
    emotion_scores = {}
    for emotion, indicators in emotion_indicators.items():
        score = 0
        for indicator in indicators:
            if indicator in text_lower:
                score += 1
        emotion_scores[emotion] = score
    
    # Additional scoring based on punctuation and emphasis
    exclamation_count = transcript_text.count('!')
    question_count = transcript_text.count('?')
    uppercase_ratio = sum(1 for c in transcript_text if c.isupper()) / len(transcript_text) if transcript_text else 0
    
    # More nuanced scoring based on text characteristics
    if exclamation_count > 0:
        # Distribute excitement points more carefully
        if any(word in text_lower for word in ['wow', 'amazing', 'incredible', 'hype']):
            emotion_scores['excitement'] += 1
        elif any(word in text_lower for word in ['haha', 'lol', 'funny', 'joke']):
            emotion_scores['humor'] += 1
        elif any(word in text_lower for word in ['fuck', 'angry', 'rage', 'hate']):
            emotion_scores['frustration'] += 1
        elif any(word in text_lower for word in ['yes', 'finally', 'success', 'victory']):
            emotion_scores['satisfaction'] += 1
        else:
            # Default excitement for general exclamations
            emotion_scores['excitement'] += 0.5
    
    # Boost confusion for questions
    if question_count > 0:
        emotion_scores['confusion'] += question_count
    
    # Boost specific emotions for high uppercase ratio
    if uppercase_ratio > 0.1:
        # Check for specific high-energy words
        if any(word in text_lower for word in ['wow', 'amazing', 'incredible']):
            emotion_scores['awe'] += 1
        elif any(word in text_lower for word in ['haha', 'lol', 'funny']):
            emotion_scores['humor'] += 1
        elif any(word in text_lower for word in ['fuck', 'angry', 'rage']):
            emotion_scores['frustration'] += 1
        else:
            emotion_scores['excitement'] += 0.5
    
    # Special case handling for specific phrases
    if 'haha' in text_lower or 'lol' in text_lower or 'funny' in text_lower:
        emotion_scores['humor'] += 2  # Strong boost for humor indicators
    
    if 'fuck' in text_lower or 'angry' in text_lower or 'rage' in text_lower:
        emotion_scores['frustration'] += 2  # Strong boost for frustration indicators
    
    if 'finally' in text_lower or 'success' in text_lower or 'victory' in text_lower:
        emotion_scores['satisfaction'] += 2  # Strong boost for satisfaction indicators
    
    if 'oops' in text_lower or 'sorry' in text_lower or 'mistake' in text_lower:
        emotion_scores['embarrassment'] += 2  # Strong boost for embarrassment indicators
    
    # Additional specific phrase matching
    if 'can\'t believe' in text_lower or 'unbelievable' in text_lower:
        emotion_scores['awe'] += 2  # Strong boost for awe indicators
    
    if 'oh no' in text_lower:
        emotion_scores['embarrassment'] += 2  # Strong boost for embarrassment
    
    if 'frustrating' in text_lower or 'frustrated' in text_lower:
        emotion_scores['frustration'] += 2  # Strong boost for frustration
    
    if 'close call' in text_lower or 'narrow' in text_lower:
        emotion_scores['relief'] += 2  # Strong boost for relief
    
    if 'best' in text_lower or 'greatest' in text_lower or 'proud' in text_lower:
        emotion_scores['pride'] += 2  # Strong boost for pride
    
    # Find the emotion with the highest score
    if emotion_scores:
        best_emotion = max(emotion_scores, key=emotion_scores.get)
        best_score = emotion_scores[best_emotion]
        
        # Only return the emotion if it has a meaningful score
        if best_score > 0:
            return best_emotion
    
    # Fallback logic based on text characteristics
    if exclamation_count > 0:
        return "excitement"
    elif question_count > 0:
        return "confusion"
    elif uppercase_ratio > 0.1:
        return "excitement"
    elif len(transcript_text.split()) < 5:
        return "confusion"  # Short text often indicates confusion
    else:
        return "confusion"  # Default fallback

def is_clip_worthy_by_model_v2(segments: List[Dict], threshold: float = 0.65, clip_id: Optional[str] = None) -> Tuple[bool, float, Dict]:
    """
    For each segment, generate OpenAI embedding, predict probability, log text and probability, and return True immediately if any prob > threshold.
    If no segment passes, return False and the highest probability.
    """
    import openai
    import numpy as np
    from joblib import load
    import os
    
    # Ensure OpenAI API key is loaded
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required. Please set it before running this script.")

    # Load model
    model = load("models/clip_classifier.pkl")
    
    debug_info = {"segment_probs": [], "clip_id": clip_id, "threshold": threshold}
    max_prob = 0.0
    best_segment = None
    print(f"🔍 DEBUG: Model prediction threshold lowered from 0.75 to {threshold}")
    
    for i, segment in enumerate(segments):
        text = segment.get("text", "")
        if not text.strip():
            continue
        response = openai.embeddings.create(model="text-embedding-ada-002", input=text)
        embedding = np.array(response.data[0].embedding).reshape(1, -1)
        prob = model.predict_proba(embedding)[0][1]
        debug_info["segment_probs"].append({"text": text, "prob": prob})
        print(f"[Segment {i+1}] Text: {text[:80]} | Probability: {prob:.3f}")
        
        # Add debug logging for threshold comparison
        if prob > threshold:
            print(f"🔍 DEBUG: Segment {i+1} triggered - Prob: {prob:.4f} > Threshold: {threshold:.4f}")
        else:
            print(f"🔍 DEBUG: Segment {i+1} below threshold - Prob: {prob:.4f} <= Threshold: {threshold:.4f}")
            
        if prob > max_prob:
            max_prob = prob
            best_segment = text
        if prob > threshold:
            debug_info["triggered_segment"] = text
            debug_info["triggered_prob"] = prob
            return True, prob, debug_info
    debug_info["max_prob"] = max_prob
    debug_info["best_segment"] = best_segment
    return False, max_prob, debug_info


if __name__ == "__main__":
    # Test the function with a dummy transcript string
    test_transcript = "That was crazy, clip that!"
    
    print("Testing clip worthiness prediction...")
    print(f"Transcript: {test_transcript}")
    
    try:
        result = is_clip_worthy_by_model(test_transcript)
        print(f"Clip is {'worthy' if result else 'not worthy'}")
    except Exception as e:
        print(f"Error during prediction: {e}")