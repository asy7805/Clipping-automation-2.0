#!/usr/bin/env python3
"""
Training script for Self Training Clipping Model.
Loads labeled data from Supabase, generates embeddings using OpenAI, trains a classifier, and saves the model.
"""

import numpy as np
import joblib
import os
from datetime import datetime
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
import logging
from supabase import create_client

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key] = value
            return True
        except Exception as e:
            print(f"Error loading .env file: {e}")
            return False
    return False

# Load environment variables at module level
load_env_file()

DATA_DIR = os.getenv("MODEL_DATA_DIR", "data/")
MODEL_DIR = os.getenv("MODEL_DIR", "models/")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_data_from_supabase() -> tuple:
    """
    Load labeled data directly from Supabase clips table.
    
    Returns:
        Tuple of (X_text, y_label) as lists
    """
    try:
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            logger.error("❌ Supabase credentials not found. Set SUPABASE_URL and SUPABASE_ANON_KEY/SUPABASE_KEY")
            return [], []
        
        # Create Supabase client
        supabase = create_client(supabase_url, supabase_key)
        
        # Query clips table for rows where label IS NOT NULL
        logger.info("🔍 Querying clips table from Supabase...")
        response = supabase.table("clips").select("transcript,label").not_.is_("label", "null").execute()
        
        if not response.data:
            logger.warning("⚠️ No labeled data found in Supabase")
            return [], []
        
        # Extract text and labels
        X_text = []
        y_label = []
        
        for row in response.data:
            text = row.get("transcript", "")
            label = row.get("label")
            
            if text and label is not None:
                X_text.append(text)
                
                # Convert label to numeric
                if isinstance(label, str):
                    if label.lower() in ['0', 'false', 'bad', 'not_worthy', '0.0']:
                        y_label.append(0)
                    elif label.lower() in ['1', 'true', 'good', 'worthy', '1.0']:
                        y_label.append(1)
                    elif label.lower() in ['2', 'excellent', 'viral', '2.0']:
                        y_label.append(2)
                    else:
                        y_label.append(0)  # Default to 0
                else:
                    y_label.append(int(float(label)))
        
        logger.info(f"✅ Loaded {len(X_text)} labeled clips from Supabase")
        logger.info(f"📊 Label distribution: {np.bincount(y_label) if y_label else 'No labels'}")
        
        return X_text, y_label
        
    except Exception as e:
        logger.error(f"❌ Error loading data from Supabase: {e}")
        return [], []

def generate_embeddings(texts: list) -> np.ndarray:
    """
    Generate embeddings from text using OpenAI semantic embeddings (v1.0+ API).
    
    Args:
        texts: List of text strings
        
    Returns:
        NumPy array of embeddings
    """
    try:
        import openai
        
        # Get OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error("❌ OpenAI API key not found. Set OPENAI_API_KEY environment variable")
            raise ValueError("OpenAI API key not found")
        
        # Configure OpenAI client (v1.0+ syntax)
        client = openai.OpenAI(api_key=openai_api_key)
        
        logger.info(f"🔢 Generating OpenAI embeddings for {len(texts)} texts...")
        
        embeddings = []
        batch_size = 100  # Process in batches to avoid rate limits
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            logger.info(f"   Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
            
            try:
                response = client.embeddings.create(
                    input=batch_texts,
                    model="text-embedding-ada-002"
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                embeddings.extend(batch_embeddings)
                
            except Exception as e:
                logger.error(f"❌ Error generating embeddings for batch {i//batch_size + 1}: {e}")
                raise
        
        embeddings_array = np.array(embeddings)
        logger.info(f"✅ Generated embeddings with shape: {embeddings_array.shape}")
        return embeddings_array
        
    except ImportError:
        logger.error("❌ OpenAI not installed. Install with: pip install openai")
        raise
    except Exception as e:
        logger.error(f"❌ Error generating embeddings: {e}")
        raise

def load_data(X_path: str = None, y_path: str = None) -> tuple:
    """
    Load text data from Supabase and generate embeddings on-the-fly.
    
    Args:
        X_path: Deprecated - no longer used
        y_path: Deprecated - no longer used
        
    Returns:
        Tuple of (X, y) as NumPy arrays where X contains embeddings
    """
    logger.info("🔍 Loading labeled data from Supabase and generating embeddings...")
    
    # Load text and labels from Supabase
    X_text, y_labels = load_data_from_supabase()
    
    if not X_text or not y_labels:
        logger.error("❌ No labeled data found in Supabase")
        raise ValueError("No labeled data found in Supabase clips table")
    
    # Verify X_text and y_labels have the same number of samples
    if len(X_text) != len(y_labels):
        logger.error(f"❌ Mismatch between text ({len(X_text)} samples) and labels ({len(y_labels)} samples)")
        raise ValueError(f"Text and labels have different lengths: {len(X_text)} vs {len(y_labels)}")
    
    # Generate embeddings from text
    logger.info("🧠 Generating embeddings from text data...")
    X_embeddings = generate_embeddings(X_text)
    
    # Convert labels to numpy array
    y = np.array(y_labels)
    
    logger.info(f"✅ Generated embeddings with shape: {X_embeddings.shape}")
    logger.info(f"✅ Loaded {len(y)} labels from Supabase")
    logger.info(f"📊 Label distribution: {np.bincount(y) if len(y) > 0 else 'No labels'}")
    logger.info(f"📊 Final dataset - X shape: {X_embeddings.shape}, y shape: {y.shape}")
    logger.info(f"📊 Unique labels: {np.unique(y)}")
    
    return X_embeddings, y

def split_data(X: np.ndarray, y: np.ndarray, test_size: float = 0.2, random_state: int = 42) -> tuple:
    """
    Split data into training and test sets.
    
    Args:
        X: Feature array
        y: Label array
        test_size: Proportion of data to use for testing
        random_state: Random seed for reproducibility
        
    Returns:
        Tuple of (X_train, X_test, y_train, y_test)
    """
    logger.info(f"📊 Splitting data: {len(X)} samples, test_size={test_size}")
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    logger.info(f"✅ Training set: {len(X_train)} samples")
    logger.info(f"✅ Test set: {len(X_test)} samples")
    logger.info(f"📊 Training label distribution: {np.bincount(y_train)}")
    logger.info(f"📊 Test label distribution: {np.bincount(y_test)}")
    
    return X_train, X_test, y_train, y_test

def train_classifier(X_train: np.ndarray, y_train: np.ndarray, random_state: int = 42) -> LogisticRegression:
    """
    Train a logistic regression classifier.
    
    Args:
        X_train: Training features
        y_train: Training labels
        random_state: Random seed for reproducibility
        
    Returns:
        Trained LogisticRegression model
    """
    logger.info("🤖 Training logistic regression classifier...")
    
    # Initialize model
    model = LogisticRegression(
        random_state=random_state,
        max_iter=1000,
        solver='liblinear',
        class_weight='balanced'
    )
    
    # Train model
    model.fit(X_train, y_train)
    
    logger.info("✅ Model training completed")
    logger.info(f"📊 Model coefficients shape: {model.coef_.shape}")
    logger.info(f"📊 Model intercept: {model.intercept_}")
    
    return model

def evaluate_model(model, X_test: np.ndarray, y_test: np.ndarray) -> tuple:
    """
    Evaluate the trained model.
    
    Args:
        model: Trained model
        X_test: Test features
        y_test: Test labels
        
    Returns:
        Tuple of (accuracy, f1_score)
    """
    logger.info("📊 Evaluating model performance...")
    
    # Make predictions
    y_pred = model.predict(X_test)
    
    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='weighted')
    
    # Print detailed results
    logger.info(f"✅ Test Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
    logger.info(f"✅ Test F1 Score: {f1:.4f} ({f1*100:.2f}%)")
    
    # Classification report
    logger.info("📋 Classification Report:")
    logger.info(classification_report(y_test, y_pred))
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    logger.info("📊 Confusion Matrix:")
    logger.info(cm)
    
    return accuracy, f1

def save_model(model, model_path: str = None) -> None:
    """
    Save the trained model to disk.
    
    Args:
        model: Trained model to save
        model_path: Path to save the model (default: models/clip_classifier.pkl)
    """
    if model_path is None:
        model_path = Path(MODEL_DIR) / "clip_classifier.pkl"
    
    # Create model directory if it doesn't exist
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save model
    joblib.dump(model, model_path)
    logger.info(f"💾 Model saved to: {model_path}")

def log_training_run_to_supabase(model_id, train_size, accuracy, f1_score, notes=None):
    """
    Log training run details to Supabase.
    
    Args:
        model_id: Unique identifier for the model
        train_size: Number of training samples
        accuracy: Test accuracy
        f1_score: Test F1 score
        notes: Additional notes
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            logger.warning("⚠️ Supabase credentials not found, skipping database logging")
            return False
        
        # Create Supabase client
        supabase = create_client(supabase_url, supabase_key)
        
        # Prepare training run data
        training_data = {
            "model_id": model_id,
            "train_size": int(train_size),
            "accuracy": float(accuracy),
            "f1_score": float(f1_score),
            "notes": notes
        }
        
        # Insert into model_training_runs table
        response = supabase.table("model_training_runs").insert(training_data).execute()
        
        if response.data:
            logger.info(f"✅ Training run logged to Supabase: model_id={model_id}, accuracy={accuracy:.3f}, f1={f1_score:.3f}")
            return True
        else:
            logger.error("❌ Failed to log training run to Supabase")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error logging training run to Supabase: {e}")
        return False

def get_smart_version(accuracy, f1_score):
    """
    Smart versioning based on performance and existing versions.
    
    Args:
        accuracy: Current model accuracy (0.0 to 1.0)
        f1_score: Current model F1 score (0.0 to 1.0) - not used for comparison
                  since it's not stored in model_registry
        
    Returns:
        str: Version string (e.g., "v1.0", "v1.1", "v2.0")
    """
    try:
        # Get Supabase credentials
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            logger.warning("⚠️ Supabase credentials not found, using timestamp versioning")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return f"v1.0.{timestamp}"
        
        # Create Supabase client
        supabase = create_client(supabase_url, supabase_key)
        
        # Get latest model from registry
        response = supabase.table("model_registry").select("*").order("created_at", desc=True).limit(1).execute()
        
        if response.data:
            latest = response.data[0]
            latest_version = latest.get("model_version", "v1.0")  # Use model_version field
            latest_accuracy = latest.get("accuracy", 0.0)
            
            # Only consider accuracy improvements since F1 is not stored in registry
            accuracy_improvement = accuracy - latest_accuracy
            
            logger.info(f"📊 Performance comparison:")
            logger.info(f"   Previous: Accuracy={latest_accuracy:.4f}")
            logger.info(f"   Current:  Accuracy={accuracy:.4f}")
            logger.info(f"   Improvement: Accuracy={accuracy_improvement:+.4f}")
            
            # Major version increment for significant improvements (>5% improvement in accuracy)
            if accuracy_improvement > 0.05:
                try:
                    major_version = int(latest_version.split(".")[0][1:]) + 1
                    new_version = f"v{major_version}.0"
                    logger.info(f"🚀 Major improvement detected! Incrementing to {new_version}")
                    return new_version
                except (ValueError, IndexError):
                    logger.warning("⚠️ Could not parse previous version, using v2.0")
                    return "v2.0"
            
            # Minor version increment for moderate improvements (>1% improvement in accuracy)
            elif accuracy_improvement > 0.01:
                try:
                    if "." in latest_version and len(latest_version.split(".")) >= 2:
                        major_version = latest_version.split(".")[0][1:]
                        minor_version = int(latest_version.split(".")[1]) + 1
                        new_version = f"v{major_version}.{minor_version}"
                        logger.info(f"📈 Moderate improvement detected! Incrementing to {new_version}")
                        return new_version
                    else:
                        new_version = f"{latest_version}.1"
                        logger.info(f"📈 Moderate improvement detected! Incrementing to {new_version}")
                        return new_version
                except (ValueError, IndexError):
                    logger.warning("⚠️ Could not parse previous version, using v1.1")
                    return "v1.1"
            
            # Patch version for minor updates or no improvement
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                new_version = f"{latest_version}.{timestamp}"
                logger.info(f"📝 Minor update, using patch version: {new_version}")
                return new_version
        
        else:
            logger.info("🎯 First model in registry, using v1.0")
            return "v1.0"
        
    except Exception as e:
        logger.error(f"❌ Error in smart versioning: {e}")
        logger.info("🔄 Falling back to timestamp versioning")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"v1.0.{timestamp}"

def main():
    """Main function to run the training pipeline"""
    try:
        # Load text data from Supabase and generate embeddings
        logger.info("🔍 Loading text data from Supabase and generating embeddings...")
        X, y = load_data()
        
        # Split data
        X_train, X_test, y_train, y_test = split_data(X, y)
        
        # Train classifier
        model = train_classifier(X_train, y_train)
        
        # Evaluate model
        accuracy, f1 = evaluate_model(model, X_test, y_test)
        
        # Save model
        model_path = Path(MODEL_DIR) / "clip_classifier.pkl"
        save_model(model, model_path)
        
        # Generate model ID and smart version
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_id = f"clip_classifier_{timestamp}"
        version = get_smart_version(accuracy, f1)  # ← Smart versioning here!
        
        # Register model in model registry
        try:
            from supabase_utils import register_model_in_registry
            
            description = f"Clip classification model trained on {len(X_train)} samples"
            file_path = str(model_path)
            notes = f"Training run with {len(X_train)} samples, test size: {len(X_test)}, F1: {f1:.4f}"
            
            registry_id = register_model_in_registry(
                version=version,
                description=description,
                accuracy=accuracy,
                file_path=file_path,
                notes=notes
            )
            
            if registry_id:
                print(f"📋 Model registered in registry with ID: {registry_id}")
                print(f"🏷️ Smart version assigned: {version}")
            else:
                print("⚠️ Failed to register model in registry")
                
        except Exception as e:
            logger.error(f"❌ Error registering model in registry: {e}")
            print("⚠️ Failed to register model in registry")
        
        # Log training run to Supabase
        notes = f"Training run with {len(X_train)} samples, test size: {len(X_test)}"
        log_training_run_to_supabase(model_id, len(X_train), accuracy, f1, notes)
        
        print(f"\n🎉 Training completed successfully!")
        print(f"📊 Final Test Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
        print(f"📊 Final Test F1 Score: {f1:.4f} ({f1*100:.2f}%)")
        print(f"💾 Model saved to: {model_path}")
        print(f"📝 Training run logged with ID: {model_id}")
        print(f"🏷️ Smart version: {version}")
        
    except Exception as e:
        logger.error(f"Error during training: {e}")
        raise

if __name__ == "__main__":
    main() 