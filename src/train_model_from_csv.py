#!/usr/bin/env python3
"""
Train enhanced model from CSV data with emotional features.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_data_from_csv():
    """Load training data from CSV file."""
    try:
        csv_path = Path("data/training_data_with_emotions.csv")
        
        if not csv_path.exists():
            logger.error(f"❌ CSV file not found: {csv_path}")
            logger.info("💡 Please export your data from Supabase and save it as 'data/training_data_with_emotions.csv'")
            return None, None, None
        
        df = pd.read_csv(csv_path)
        logger.info(f"✅ Loaded {len(df)} clips from CSV")
        
        # Check required columns
        required_columns = ['transcript', 'label', 'emotion_label']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.error(f"❌ Missing required columns: {missing_columns}")
            return None, None, None
        
        return df, None, None
        
    except Exception as e:
        logger.error(f"❌ Error loading CSV data: {e}")
        return None, None, None

def create_enhanced_feature_vector(row):
    """Create enhanced feature vector from CSV row."""
    transcript = row.get('transcript', '')
    emotion = row.get('emotion_label', '')
    confidence = row.get('emotion_confidence', 0.5)
    content_type = row.get('content_type', '')
    source = row.get('source', '')
    
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
    features['emotion_confidence'] = confidence or 0.5
    
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

def train_enhanced_model_from_csv():
    """Train enhanced model from CSV data."""
    try:
        # Load data
        df, _, _ = load_data_from_csv()
        if df is None:
            return False
        
        # Create feature vectors
        X_features = []
        y_labels = []
        emotion_labels = []
        
        for _, row in df.iterrows():
            label = row.get('label')
            emotion = row.get('emotion_label')
            
            if pd.notna(label) and pd.notna(emotion):
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
                
                # Create feature vector
                feature_vector = create_enhanced_feature_vector(row)
                X_features.append(feature_vector)
                emotion_labels.append(emotion)
        
        if not X_features:
            logger.error("❌ No valid data found for training")
            return False
        
        # Convert to DataFrame
        X_df = pd.DataFrame(X_features)
        feature_names = X_df.columns.tolist()
        
        logger.info(f"🧠 Training enhanced model with {len(feature_names)} features")
        logger.info(f"📊 Feature names: {feature_names}")
        logger.info(f"🎭 Emotion distribution: {pd.Series(emotion_labels).value_counts().to_dict()}")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_df, y_labels, test_size=0.2, random_state=42, stratify=y_labels
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
        
        # Save model
        model_dir = Path("models")
        model_dir.mkdir(exist_ok=True)
        
        model_path = model_dir / "enhanced_clip_classifier_from_csv.pkl"
        joblib.dump(model, model_path)
        
        logger.info(f"💾 Enhanced model saved to {model_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error training model from CSV: {e}")
        return False

if __name__ == "__main__":
    success = train_enhanced_model_from_csv()
    sys.exit(0 if success else 1)
