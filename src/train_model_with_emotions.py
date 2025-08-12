#!/usr/bin/env python3
"""
Enhanced training script that incorporates emotional labels as features.
This builds on your existing training pipeline but adds emotional context.
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from supabase import create_client
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_supabase_client():
    """Get Supabase client with credentials from environment."""
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            logger.error("❌ Supabase credentials not found. Set SUPABASE_URL and SUPABASE_ANON_KEY/SUPABASE_KEY")
            return None
        
        logger.info("✅ Supabase credentials loaded successfully")
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        logger.error(f"❌ Error creating Supabase client: {e}")
        return None

def load_data_with_emotions():
    """
    Load labeled data with emotional labels from Supabase.
    
    Returns:
        Tuple of (X_features, y_labels, emotion_labels) as lists
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            return [], [], []
        
        # Query clips table for labeled clips with emotion labels
        logger.info("🔍 Loading clips with emotion labels from Supabase...")
        response = supabase.table("clips").select(
            "transcript,label,emotion_label,emotion_confidence,content_type,source"
        ).not_.is_("label", "null").execute()
        
        if not response.data:
            logger.warning("⚠️ No labeled clips with emotion data found")
            return [], [], []
        
        # Extract features and labels
        X_features = []
        y_labels = []
        emotion_labels = []
        
        for row in response.data:
            transcript = row.get("transcript", "")
            label = row.get("label")
            emotion = row.get("emotion_label")
            confidence = row.get("emotion_confidence", 0.5)
            content_type = row.get("content_type", "")
            source = row.get("source", "")
            
            if transcript and label is not None:
                # Convert label to numeric
                if isinstance(label, str):
                    if label.lower() in ['0', 'false', 'bad', 'not_worthy', '0.0']:
                        y_labels.append(0)
                    elif label.lower() in ['1', 'true', 'good', 'worthy', '1.0']:
                        y_labels.append(1)
                    elif label.lower() in ['2', 'excellent', 'viral', '2.0']:
                        y_labels.append(2)
                    else:
                        y_labels.append(0)
                else:
                    y_labels.append(int(float(label)))
                
                # Create feature vector with emotional context
                feature_vector = create_enhanced_feature_vector(
                    transcript, emotion, confidence, content_type, source
                )
                X_features.append(feature_vector)
                emotion_labels.append(emotion)
        
        logger.info(f"✅ Loaded {len(X_features)} clips with emotion data")
        logger.info(f"📊 Label distribution: {np.bincount(y_labels) if y_labels else 'No labels'}")
        logger.info(f"🎭 Emotion distribution: {pd.Series(emotion_labels).value_counts().to_dict()}")
        
        return X_features, y_labels, emotion_labels
        
    except Exception as e:
        logger.error(f"❌ Error loading data with emotions: {e}")
        return [], [], []

def create_enhanced_feature_vector(transcript, emotion, confidence, content_type, source):
    """
    Create enhanced feature vector incorporating emotional context.
    
    Args:
        transcript: Text transcript
        emotion: Emotional label
        confidence: Emotion confidence score
        content_type: Content type
        source: Source platform
        
    Returns:
        dict: Feature vector with emotional context
    """
    # Base features from transcript
    features = {
        'text_length': len(transcript),
        'word_count': len(transcript.split()),
        'avg_word_length': np.mean([len(word) for word in transcript.split()]) if transcript.split() else 0,
        'exclamation_count': transcript.count('!'),
        'question_count': transcript.count('?'),
        'uppercase_ratio': sum(1 for c in transcript if c.isupper()) / len(transcript) if transcript else 0,
    }
    
    # Emotional features
    emotion_mapping = {
        'excitement': 1, 'humor': 2, 'surprise': 3, 'awe': 4, 'tension': 5,
        'frustration': 6, 'satisfaction': 7, 'confusion': 8, 'nostalgia': 9,
        'pride': 10, 'embarrassment': 11, 'relief': 12, 'disappointment': 13,
        'curiosity': 14, 'anticipation': 15, 'clutch': 16, 'rage': 17,
        'hype': 18, 'tilt': 19, 'flow': 20
    }
    
    features['emotion_encoded'] = emotion_mapping.get(emotion, 0)
    # Remove emotion_confidence since it's simulated and doesn't reflect actual clips
    # features['emotion_confidence'] = confidence or 0.5
    
    # Content type features
    content_type_mapping = {
        'joke': 1, 'reaction': 2, 'insight': 3, 'hype': 4, 'boring': 5
    }
    features['content_type_encoded'] = content_type_mapping.get(content_type, 0)
    
    # Source features
    source_mapping = {'twitch': 1, 'tiktok': 2, 'youtube': 3}
    features['source_encoded'] = source_mapping.get(source, 0)
    
    # Emotional intensity features
    high_energy_emotions = ['excitement', 'hype', 'rage', 'clutch']
    features['is_high_energy'] = 1 if emotion in high_energy_emotions else 0
    
    positive_emotions = ['excitement', 'humor', 'awe', 'satisfaction', 'pride', 'hype', 'flow']
    features['is_positive_emotion'] = 1 if emotion in positive_emotions else 0
    
    negative_emotions = ['frustration', 'confusion', 'embarrassment', 'disappointment', 'rage', 'tilt']
    features['is_negative_emotion'] = 1 if emotion in negative_emotions else 0
    
    return features

def train_enhanced_model(X_features, y_labels):
    """
    Train enhanced model with emotional features.
    
    Args:
        X_features: List of feature dictionaries
        y_labels: List of labels
        
    Returns:
        Trained model and feature names
    """
    try:
        # Convert to DataFrame
        df = pd.DataFrame(X_features)
        feature_names = df.columns.tolist()
        
        logger.info(f"🧠 Training enhanced model with {len(feature_names)} features")
        logger.info(f"📊 Feature names: {feature_names}")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            df, y_labels, test_size=0.2, random_state=42, stratify=y_labels
        )
        
        # Train model
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"✅ Model trained successfully")
        logger.info(f"📈 Accuracy: {accuracy:.3f}")
        logger.info(f"📊 Classification Report:")
        logger.info(classification_report(y_test, y_pred))
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': feature_names,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        logger.info(f"🎯 Top 10 Most Important Features:")
        for _, row in feature_importance.head(10).iterrows():
            logger.info(f"   {row['feature']}: {row['importance']:.3f}")
        
        return model, feature_names, accuracy
        
    except Exception as e:
        logger.error(f"❌ Error training enhanced model: {e}")
        return None, None, 0

def save_enhanced_model(model, feature_names, accuracy):
    """Save the enhanced model with metadata."""
    try:
        model_dir = Path("models")
        model_dir.mkdir(exist_ok=True)
        
        # Save model
        model_path = model_dir / "enhanced_clip_classifier.pkl"
        joblib.dump(model, model_path)
        
        # Save metadata
        metadata = {
            'accuracy': accuracy,
            'feature_names': feature_names,
            'model_type': 'RandomForestClassifier',
            'includes_emotions': True,
            'created_at': pd.Timestamp.now().isoformat()
        }
        
        metadata_path = model_dir / "enhanced_model_metadata.json"
        import json
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"💾 Enhanced model saved to {model_path}")
        logger.info(f"📋 Metadata saved to {metadata_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving enhanced model: {e}")
        return False

def main():
    """Main function to train enhanced model with emotions."""
    logger.info("🚀 Starting enhanced model training with emotional features...")
    
    # Load data with emotions
    X_features, y_labels, emotion_labels = load_data_with_emotions()
    
    if not X_features:
        logger.error("❌ No data loaded, cannot train model")
        return False
    
    # Train enhanced model
    model, feature_names, accuracy = train_enhanced_model(X_features, y_labels)
    
    if model is None:
        logger.error("❌ Model training failed")
        return False
    
    # Save enhanced model
    if save_enhanced_model(model, feature_names, accuracy):
        logger.info("🎉 Enhanced model training completed successfully!")
        return True
    else:
        logger.error("❌ Failed to save enhanced model")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 