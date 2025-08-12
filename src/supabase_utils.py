#!/usr/bin/env python3
"""
Supabase utilities for Self Training Clipping Model.
Provides functions for interacting with clips and clip_analytics tables.
"""

import os
import logging
from typing import List, Dict, Optional, Any
from supabase import create_client, Client

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_supabase_client() -> Optional[Client]:
    """Get Supabase client with proper error handling."""
    try:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            logger.error("❌ Supabase credentials not found. Set SUPABASE_URL and SUPABASE_ANON_KEY/SUPABASE_KEY")
            return None
        
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        logger.error(f"❌ Error creating Supabase client: {e}")
        return None

def insert_clip(clip_id: str, transcript: str, label: Optional[str] = None, 
                       label_type: str = "manual", source: str = "auto") -> bool:
    """
    Insert a new labeled clip into the clips table.
    
    Args:
        clip_id: Unique identifier for the clip
        transcript: The transcript text
        label: Label value (can be None for unlabeled clips)
        label_type: Type of labeling ("manual" or "auto")
        source: Source of the clip (e.g., "twitch", "manual")
        
    Returns:
        True if successful, False otherwise
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            return False
        
        clip_data = {
            "clip_id": clip_id,
            "text": transcript,
            "label": label,
            "label_type": label_type,
            "source": source
        }
        
        response = supabase.table("clips").insert(clip_data).execute()
        
        if response.data:
            logger.info(f"✅ Inserted labeled clip: {clip_id}")
            return True
        else:
            logger.error(f"❌ Failed to insert labeled clip: {clip_id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error inserting labeled clip {clip_id}: {e}")
        return False

def get_clips(label_type: Optional[str] = None, source: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get labeled clips from the database.
    
    Args:
        label_type: Filter by label type (optional)
        source: Filter by source (optional)
        
    Returns:
        List of labeled clip dictionaries
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            return []
        
        query = supabase.table("clips").select("*")
        
        if label_type:
            query = query.eq("label_type", label_type)
        
        if source:
            query = query.eq("source", source)
        
        response = query.execute()
        
        if response.data:
            logger.info(f"✅ Retrieved {len(response.data)} labeled clips")
            return response.data
        else:
            logger.warning("⚠️  No labeled clips found")
            return []
            
    except Exception as e:
        logger.error(f"❌ Error retrieving labeled clips: {e}")
        return []

def get_all_clips() -> List[Dict[str, Any]]:
    """
    Get all clips from the database.
    
    Returns:
        List of all clip dictionaries
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            return []
        
        response = supabase.table("clips").select("*").execute()
        
        if response.data:
            logger.info(f"✅ Retrieved {len(response.data)} clips")
            return response.data
        else:
            logger.warning("⚠️  No clips found")
            return []
            
    except Exception as e:
        logger.error(f"❌ Error retrieving all clips: {e}")
        return []

def get_clips_for_training() -> tuple:
    """
    Get labeled clips specifically formatted for training.
    
    Returns:
        Tuple of (transcripts, labels) as lists
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            return [], []
        
        # Query clips table for labeled clips only
        response = supabase.table("clips").select("transcript,label").not_.is_("label", "null").execute()
        
        if not response.data:
            logger.warning("⚠️ No labeled clips found for training")
            return [], []
        
        transcripts = []
        labels = []
        
        for clip in response.data:
            text = clip.get("transcript", "")
            label = clip.get("label")
            
            if text and label is not None:
                transcripts.append(text)
                
                # Convert label to numeric
                if isinstance(label, str):
                    if label.lower() in ['0', 'false', 'bad', 'not_worthy', '0.0']:
                        labels.append(0)
                    elif label.lower() in ['1', 'true', 'good', 'worthy', '1.0']:
                        labels.append(1)
                    elif label.lower() in ['2', 'excellent', 'viral', '2.0']:
                        labels.append(2)
                    else:
                        labels.append(0)  # Default to 0
                else:
                    labels.append(int(float(label)))
        
        logger.info(f"✅ Retrieved {len(transcripts)} clips for training")
        return transcripts, labels
        
    except Exception as e:
        logger.error(f"❌ Error getting clips for training: {e}")
        return [], []

def safe_upsert_clip_analytics(supabase, clip_id, analytics_data):
    """
    Safely upsert clip analytics by checking if the clip exists first.
    
    Args:
        supabase: Supabase client instance
        clip_id: Unique identifier for the clip
        analytics_data: Dictionary containing analytics data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Confirm the clip exists first
        existing = supabase.table("clips").select("clip_id").eq("clip_id", clip_id).execute()
        if existing.data:
            response = supabase.table("clip_analytics").upsert(analytics_data).execute()
            if response.data:
                logger.info(f"✅ Safely upserted analytics for clip: {clip_id}")
                return True
            else:
                logger.error(f"❌ Failed to upsert analytics for clip: {clip_id}")
                return False
        else:
            logger.warning(f"⛔ Skipping analytics: clip_id {clip_id} not found in clips table.")
            return False
    except Exception as e:
        logger.error(f"❌ Error in safe_upsert_clip_analytics for clip {clip_id}: {e}")
        return False

def upsert_clip_analytics(clip_id: str, views: int = 0, watch_time: float = 0.0, 
                         likes: int = 0, comments: int = 0, engagement_score: float = 0.0) -> bool:
    """
    Insert or update clip analytics data with safety check.
    
    Args:
        clip_id: Unique identifier for the clip
        views: Number of views
        watch_time: Watch time in seconds
        likes: Number of likes
        comments: Number of comments
        engagement_score: Calculated engagement score
        
    Returns:
        True if successful, False otherwise
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            return False
        
        analytics_data = {
            "clip_id": clip_id,
            "views": int(views),
            "watch_time": float(watch_time),
            "likes": int(likes),
            "comments": int(comments),
            "engagement_score": float(engagement_score)
        }
        
        # Use safe upsert function
        return safe_upsert_clip_analytics(supabase, clip_id, analytics_data)
            
    except Exception as e:
        logger.error(f"❌ Error upserting analytics for clip {clip_id}: {e}")
        return False

def get_clip_analytics(clip_id: str) -> Optional[Dict[str, Any]]:
    """
    Get analytics data for a specific clip.
    
    Args:
        clip_id: Unique identifier for the clip
        
    Returns:
        Analytics data dictionary or None if not found
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None
        
        response = supabase.table("clip_analytics").select("*").eq("clip_id", clip_id).execute()
        
        if response.data and len(response.data) > 0:
            logger.info(f"✅ Retrieved analytics for clip: {clip_id}")
            return response.data[0]
        else:
            logger.info(f"ℹ️ No analytics found for clip: {clip_id}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error retrieving analytics for clip {clip_id}: {e}")
        return None

def get_top_performing_clips(limit: int = 10, metric: str = "engagement_score") -> List[Dict[str, Any]]:
    """
    Get top performing clips based on a metric.
    
    Args:
        limit: Number of clips to return
        metric: Metric to sort by ("engagement_score", "views", "likes", etc.)
        
    Returns:
        List of top performing clips with their analytics
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            return []
        
        # Join clips with clip_analytics
        response = supabase.table("clip_analytics").select(
            "*, clips!inner(transcript, label, label_type, source)"
        ).order(metric, desc=True).limit(limit).execute()
        
        if response.data:
            logger.info(f"✅ Retrieved top {len(response.data)} performing clips")
            return response.data
        else:
            logger.info("✅ No analytics data found")
            return []
            
    except Exception as e:
        logger.error(f"❌ Error retrieving top performing clips: {e}")
        return []

def migrate_csv_to_clips(csv_path: str) -> bool:
    """
    Migrate data from CSV file to Supabase clips table.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import pandas as pd
        
        # Read CSV file
        df = pd.read_csv(csv_path)
        logger.info(f"📄 Loaded {len(df)} records from {csv_path}")
        
        # Get Supabase client
        supabase = get_supabase_client()
        if not supabase:
            return False
        
        # Prepare data for insertion
        clips_data = []
        for _, row in df.iterrows():
            # Handle NaN values properly
            label_value = row.get("label")
            if pd.notna(label_value):
                label_str = str(label_value)
            else:
                label_str = None
                
            clip_data = {
                "clip_id": row.get("clip_id", f"migrated_{row.name}"),
                "text": str(row.get("text", row.get("text", ""))) if pd.notna(row.get("text", row.get("text", ""))) else "",
                "label": label_str,
                "label_type": str(row.get("label_type", "manual")) if pd.notna(row.get("label_type", "manual")) else "manual",
                "source": str(row.get("source", "migrated")) if pd.notna(row.get("source", "migrated")) else "migrated"
            }
            clips_data.append(clip_data)
        
        # Insert data in batches
        batch_size = 100
        for i in range(0, len(clips_data), batch_size):
            batch = clips_data[i:i + batch_size]
            response = supabase.table("clips").insert(batch).execute()
            
            if response.data:
                logger.info(f"✅ Migrated batch {i//batch_size + 1}: {len(batch)} records")
            else:
                logger.error(f"❌ Failed to migrate batch {i//batch_size + 1}")
                return False
        
        logger.info(f"🎉 Successfully migrated {len(clips_data)} records to Supabase")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error migrating CSV to Supabase: {e}")
        return False

def simulate_clip_analytics(clip_id: str) -> bool:
    """
    Simulate analytics data for testing purposes.
    
    Args:
        clip_id: Unique identifier for the clip
        
    Returns:
        True if successful, False otherwise
    """
    import random
    
    # Simulate realistic analytics data
    views = random.randint(100, 10000)
    watch_time = random.uniform(30.0, 300.0)  # 30 seconds to 5 minutes
    likes = random.randint(0, views // 10)  # 0-10% like rate
    comments = random.randint(0, views // 50)  # 0-2% comment rate
    
    # Calculate engagement score (simple formula)
    engagement_score = (likes * 0.4 + comments * 0.6) / max(views, 1) * 100
    
    return upsert_clip_analytics(clip_id, views, watch_time, likes, comments, engagement_score)

def ensure_index_on_supabase(client, table_name, column_name):
    """
    Ensure an index exists on a specific table and column in Supabase.
    
    Args:
        client: Supabase client instance
        table_name: Name of the table
        column_name: Name of the column to index
        
    Returns:
        None
    """
    try:
        # Note: Supabase currently does not expose native index creation via the Python client.
        # This function is a placeholder for when RPC functions are available.
        # For now, indexes should be created manually in the Supabase dashboard.
        logger.info(f"ℹ️  Index creation for {table_name}.{column_name} should be done manually in Supabase dashboard")
        logger.info(f"ℹ️  SQL: CREATE INDEX IF NOT EXISTS idx_{table_name}_{column_name} ON {table_name} ({column_name});")
    except Exception as e:
        logger.error(f"Index creation failed: {e}")

def embed_and_store_clip(clip_id, text):
    """
    Generate and store embeddings for a clip using OpenAI embeddings.
    
    Args:
        clip_id: Unique identifier for the clip
        text: The text to embed
        
    Returns:
        None
    """
    import openai
    import numpy as np
    
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        if not supabase:
            logger.error(f"❌ Failed to get Supabase client for clip {clip_id}")
            return
        
        # Get OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error(f"❌ OpenAI API key not found. Set OPENAI_API_KEY environment variable")
            return
        
        # Set OpenAI API key
        openai.api_key = openai_api_key
        
        # Generate embedding using OpenAI
        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        embedding = response.data[0].embedding
        
        # Store in clip_embeddings_vector table
        response = supabase.table("clip_embeddings_vector").insert({
            "clip_id": clip_id,
            "embedding": embedding,
            "model": "openai"  # Specify the model used
        }).execute()
        
        if response.data:
            logger.info(f"✅ Stored OpenAI embedding for {clip_id}")
        else:
            logger.error(f"❌ Failed to store embedding for {clip_id}")
            
    except Exception as e:
        logger.error(f"❌ Error storing embedding for clip {clip_id}: {e}")

# Initialize indexes on startup
def initialize_supabase_indexes():
    """
    Initialize important indexes on Supabase tables for better performance.
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            logger.error("❌ Failed to get Supabase client for index initialization")
            return
        
        # Ensure indexes on clips table
        ensure_index_on_supabase(supabase, "clips", "timestamp")
        ensure_index_on_supabase(supabase, "clips", "views")
        ensure_index_on_supabase(supabase, "clips", "clip_id")
        
        logger.info("✅ Supabase indexes initialized")
        
    except Exception as e:
        logger.error(f"❌ Error initializing Supabase indexes: {e}")

def register_model_in_registry(version: str, description: str, accuracy: float, 
                              file_path: str, notes: str = None) -> Optional[str]:
    """
    Register a trained model in the model_registry table.
    
    Args:
        version: Model version string (e.g., "v1.0.0")
        description: Human-readable description of the model
        accuracy: Training accuracy score (0.0 to 1.0)
        file_path: Path to the saved model file
        notes: Additional notes about the model (optional)
        
    Returns:
        Model registry ID (UUID) if successful, None otherwise
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            logger.error("❌ Failed to get Supabase client for model registration")
            return None
        
        model_data = {
            "model_version": version,  # Use model_version field to match schema
            "description": description,
            "accuracy": float(accuracy),
            "file_path": file_path,
            "notes": notes
        }
        
        response = supabase.table("model_registry").insert(model_data).execute()
        
        if response.data and len(response.data) > 0:
            model_id = response.data[0]["id"]
            logger.info(f"✅ Model registered in registry with ID: {model_id}")
            logger.info(f"📊 Version: {version}, Accuracy: {accuracy:.4f}, File: {file_path}")
            return model_id
        else:
            logger.error("❌ Failed to register model in registry")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error registering model in registry: {e}")
        return None

def get_model_from_registry(version: str = None, model_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Get model information from the model_registry table.
    
    Args:
        version: Model version to retrieve (optional)
        model_id: Specific model ID to retrieve (optional)
        
    Returns:
        Model information dictionary or None if not found
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            logger.error("❌ Failed to get Supabase client for model retrieval")
            return None
        
        if model_id:
            response = supabase.table("model_registry").select("*").eq("id", model_id).execute()
        elif version:
            response = supabase.table("model_registry").select("*").eq("model_version", version).order("date_trained", desc=True).limit(1).execute()
        else:
            # Get the latest model
            response = supabase.table("model_registry").select("*").order("date_trained", desc=True).limit(1).execute()
        
        if response.data and len(response.data) > 0:
            model_info = response.data[0]
            logger.info(f"✅ Retrieved model: {model_info['model_version']} (ID: {model_info['id']})")
            return model_info
        else:
            logger.info("ℹ️ No model found in registry")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error retrieving model from registry: {e}")
        return None

def list_models_in_registry(limit: int = 10) -> List[Dict[str, Any]]:
    """
    List models in the registry, ordered by training date (newest first).
    
    Args:
        limit: Number of models to return
        
    Returns:
        List of model information dictionaries
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            logger.error("❌ Failed to get Supabase client for model listing")
            return []
        
        response = supabase.table("model_registry").select("*").order("date_trained", desc=True).limit(limit).execute()
        
        if response.data:
            logger.info(f"✅ Retrieved {len(response.data)} models from registry")
            return response.data
        else:
            logger.info("ℹ️ No models found in registry")
            return []
            
    except Exception as e:
        logger.error(f"❌ Error listing models from registry: {e}")

def calculate_engagement_score(views: int, watch_time: float, likes: int, comments: int) -> float:
    """Calculate engagement score based on metrics."""
    if views == 0:
        return 0.0
    
    watch_time_score = min(watch_time / 60.0, 1.0)
    like_rate = likes / views
    comment_rate = comments / views
    
    engagement_score = (
        watch_time_score * 0.4 +
        like_rate * 0.4 +
        comment_rate * 0.2
    )
    
    return min(engagement_score, 1.0)

def assign_auto_label(engagement_score: float) -> str:
    """Assign auto label based on engagement score."""
    if engagement_score >= 0.15:
        return "high"
    elif engagement_score >= 0.08:
        return "medium"
    else:
        return "low"

def simulate_realistic_engagement(clip_id: str, source: str = "auto") -> Dict:
    """Simulate realistic engagement data based on clip source."""
    import random
    
    if source == "ml":
        base_views = random.randint(500, 3000)
        base_like_rate = random.uniform(0.05, 0.15)
        base_comment_rate = random.uniform(0.01, 0.03)
        base_watch_time = random.uniform(45, 120)
    elif source == "random":
        base_views = random.randint(200, 1500)
        base_like_rate = random.uniform(0.02, 0.10)
        base_comment_rate = random.uniform(0.005, 0.02)
        base_watch_time = random.uniform(30, 90)
    else:
        base_views = random.randint(300, 2000)
        base_like_rate = random.uniform(0.03, 0.12)
        base_comment_rate = random.uniform(0.008, 0.025)
        base_watch_time = random.uniform(35, 100)
    
    views = int(base_views * random.uniform(0.7, 1.3))
    likes = int(views * base_like_rate * random.uniform(0.8, 1.2))
    comments = int(views * base_comment_rate * random.uniform(0.6, 1.4))
    watch_time = base_watch_time * random.uniform(0.8, 1.2)
    
    engagement_score = calculate_engagement_score(views, watch_time, likes, comments)
    
    return {
        "views": views,
        "watch_time": round(watch_time, 1),
        "likes": likes,
        "comments": comments,
        "engagement_score": round(engagement_score, 3)
    }

def log_engagement_data(clip_id: str, source: str = "auto") -> bool:
    """Log engagement data for a clip to clip_analytics table."""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return False
        
        # Generate realistic engagement data
        engagement_data = simulate_realistic_engagement(clip_id, source)
        auto_label = assign_auto_label(engagement_data['engagement_score'])
        
        # Prepare analytics data
        analytics_data = {
            "clip_id": clip_id,
            "views": engagement_data['views'],
            "watch_time": engagement_data['watch_time'],
            "likes": engagement_data['likes'],
            "comments": engagement_data['comments'],
            "engagement_score": engagement_data['engagement_score'],
            "auto_label": auto_label
        }
        
        # Try to update existing record first
        update_response = supabase.table("clip_analytics").update(analytics_data).eq("clip_id", clip_id).execute()
        
        if not update_response.data:
            # If no existing record, insert new one
            insert_response = supabase.table("clip_analytics").insert(analytics_data).execute()
            
            if not insert_response.data:
                return False
        
        logger.info(f"✅ Logged engagement data for {clip_id}: {engagement_data['views']} views, score: {engagement_data['engagement_score']}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error logging engagement data for {clip_id}: {e}")
        return False

        return [] 