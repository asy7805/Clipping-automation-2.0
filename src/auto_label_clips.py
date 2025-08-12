#!/usr/bin/env python3
"""
Auto-labeling script for clips based on engagement metrics.
Calculates engagement scores and assigns automatic labels based on views and engagement.
Now integrated with clip_analytics table for real-time engagement tracking.
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path
import sys
import logging

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = os.getenv("MODEL_DATA_DIR", "data/")

# Import analytics functions
try:
    from clip_analytics import log_clip_analytics, update_clip_metrics, get_clip_analytics_data
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    logger.warning("Clip analytics module not available")

def calculate_engagement_score(row):
    """
    Calculate engagement score based on watch_time, likes, comments, and views.
    
    Args:
        row: Pandas Series containing clip data
        
    Returns:
        float: Calculated engagement score
    """
    views = row.get('views', 0)
    watch_time = row.get('watch_time', 0)
    likes = row.get('likes', 0)
    comments = row.get('comments', 0)
    
    # Calculate engagement score
    engagement_score = (
        (watch_time / 15) +
        (likes / max(1, views)) * 2 +
        (comments / max(1, views))
    )
    
    return engagement_score

def assign_auto_label(views, engagement_score):
    """
    Assign auto_label based on views and engagement score.
    
    Args:
        views: Number of views
        engagement_score: Calculated engagement score
        
    Returns:
        float: Auto label (0, 0.5, or 1)
    """
    if views > 1000 or engagement_score > 3.0:
        return 1
    elif 500 < views <= 1000 or engagement_score > 2.0:
        return 0.5
    else:
        return 0

def assign_content_type(auto_label, transcript_text=None):
    """
    Assign content type based on auto_label value and transcript content.
    
    Args:
        auto_label: Auto label value
        transcript_text: Optional transcript text for content-based labeling
        
    Returns:
        str: Content type ('joke', 'reaction', 'insight', 'hype', 'boring', None)
    """
    # If auto_label is 0, it's likely boring
    if auto_label == 0:
        return 'boring'
    
    # For auto_label == 1 (high quality), try to determine content type
    if auto_label == 1 and transcript_text:
        transcript_lower = transcript_text.lower()
        
        # Simple keyword-based classification
        if any(word in transcript_lower for word in ['haha', 'lol', 'funny', 'joke', 'hilarious', 'comedy']):
            return 'joke'
        elif any(word in transcript_lower for word in ['wow', 'omg', 'amazing', 'incredible', 'unbelievable']):
            return 'reaction'
        elif any(word in transcript_lower for word in ['think', 'believe', 'because', 'reason', 'analysis']):
            return 'insight'
        elif any(word in transcript_lower for word in ['hype', 'excited', 'pumped', 'let\'s go', 'awesome']):
            return 'hype'
    
    # No clear content type determined
    return None

def assign_labeling_method(auto_label):
    """
    Assign labeling method based on auto_label value.
    
    Args:
        auto_label: Auto label value
        
    Returns:
        str: Labeling method ('auto', 'review_needed', 'manual')
    """
    if auto_label == 0.5:
        return 'review_needed'
    elif auto_label in [0, 1]:
        return 'auto'
    else:
        return 'manual'

def log_clip_analytics_data(clip_id: str, engagement_data: dict, auto_label: str = None):
    """
    Log analytics data for a clip to the clip_analytics table.
    
    Args:
        clip_id: The unique identifier for the clip
        engagement_data: Dictionary containing engagement metrics
        auto_label: The predicted label from the model
    """
    if not ANALYTICS_AVAILABLE:
        logger.warning("Analytics not available, skipping analytics logging")
        return False
    
    try:
        # Log initial analytics if clip doesn't exist in analytics table
        existing_analytics = get_clip_analytics_data(clip_id)
        
        if not existing_analytics:
            # Log initial analytics
            success = log_clip_analytics(clip_id, auto_label)
            if success:
                logger.info(f"✅ Initial analytics logged for clip: {clip_id}")
            else:
                logger.warning(f"⚠️  Failed to log initial analytics for clip: {clip_id}")
        
        # Update engagement metrics
        success = update_clip_metrics(
            clip_id,
            views=engagement_data.get('views', 0),
            likes=engagement_data.get('likes', 0),
            comments=engagement_data.get('comments', 0),
            watch_time=engagement_data.get('watch_time', 0),
            auto_label=auto_label
        )
        
        if success:
            logger.info(f"✅ Analytics updated for clip: {clip_id}")
            return True
        else:
            logger.warning(f"⚠️  Failed to update analytics for clip: {clip_id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error logging analytics for {clip_id}: {e}")
        return False

def auto_label_clips(csv_path=None):
    if csv_path is None:
        csv_path = Path(DATA_DIR) / "clips.csv"
    """
    Main function to auto-label clips based on engagement metrics.
    
    Args:
        csv_path: Path to the clips.csv file
    """
    
    # Check if file exists
    if not os.path.exists(csv_path):
        print(f"❌ File not found: {csv_path}")
        return
    
    print(f"📊 Loading data from {csv_path}")
    
    # Load the CSV file
    df = pd.read_csv(csv_path)
    
    print(f"✅ Loaded {len(df)} clips")
    
    # Check for required columns
    required_columns = ['views', 'watch_time', 'likes', 'comments']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        print(f"⚠️  Missing columns: {missing_columns}")
        print("📝 Available columns:", list(df.columns))
        print("🔧 Adding missing columns with default values...")
        
        # Add missing columns with default values
        for col in missing_columns:
            df[col] = 0
    
    print("🧮 Calculating engagement scores...")
    
    # Calculate engagement scores
    df['engagement_score'] = df.apply(calculate_engagement_score, axis=1)
    
    print("🏷️  Assigning auto labels...")
    
    # Assign auto labels
    df['auto_label'] = df.apply(
        lambda row: assign_auto_label(row['views'], row['engagement_score']), 
        axis=1
    )
    
    print("📋 Assigning label types...")
    
    # Assign content types and labeling methods
    df['content_type'] = df.apply(
        lambda row: assign_content_type(row['auto_label'], row.get('text', '')), 
        axis=1
    )
    
    df['labeling_method'] = df.apply(
        lambda row: assign_labeling_method(row['auto_label']), 
        axis=1
    )
    
    # Print summary statistics
    print("\n📈 Auto-labeling Summary:")
    print("-" * 40)
    print(f"Total clips: {len(df)}")
    print(f"Auto label 1 (high quality): {len(df[df['auto_label'] == 1])}")
    print(f"Auto label 0.5 (review needed): {len(df[df['auto_label'] == 0.5])}")
    print(f"Auto label 0 (low quality): {len(df[df['auto_label'] == 0])}")
    print(f"Average engagement score: {df['engagement_score'].mean():.2f}")
    print(f"Average views: {df['views'].mean():.0f}")
    
    # Save the updated DataFrame
    print(f"\n💾 Saving updated data to {csv_path}")
    df.to_csv(csv_path, index=False)
    
    # Generate and store embeddings for new clips
    print("🧠 Generating embeddings for new clips...")
    try:
        from supabase_utils import embed_and_store_clip
        
        new_clips = []
        for _, row in df.iterrows():
            clip_data = {
                "clip_id": row.get("clip_id", f"clip_{row.name}"),
                "text": row.get("text", row.get("text", "")),
                "label": row.get("label"),
                "embedding_stored": False  # We'll check if embedding exists
            }
            new_clips.append(clip_data)
        
        # Process clips and generate embeddings
        for clip in new_clips:
            if clip["label"] is not None and not clip.get("embedding_stored", False):
                embed_and_store_clip(clip["clip_id"], clip["text"])
                
        print(f"✅ Generated embeddings for {len(new_clips)} clips")
        
    except Exception as e:
        print(f"⚠️  Error generating embeddings: {e}")
    
    # Log analytics data for each clip
    print("📊 Logging analytics data...")
    analytics_logged = 0
    
    for _, row in df.iterrows():
        clip_id = row.get("clip_id", f"clip_{row.name}")
        auto_label = str(row.get("auto_label", ""))
        
        # Prepare engagement data
        engagement_data = {
            "views": row.get("views", 0),
            "likes": row.get("likes", 0),
            "comments": row.get("comments", 0),
            "watch_time": row.get("watch_time", 0)
        }
        
        # Log analytics data
        if log_clip_analytics_data(clip_id, engagement_data, auto_label):
            analytics_logged += 1
    
    print(f"✅ Analytics logged for {analytics_logged}/{len(df)} clips")
    
    print("✅ Auto-labeling completed successfully!")
    
    return df

def main():
    """Main function to run the auto-labeling pipeline."""
    try:
        # Initialize Supabase indexes
        try:
            from supabase_utils import initialize_supabase_indexes
            initialize_supabase_indexes()
        except Exception as e:
            print(f"⚠️  Error initializing Supabase indexes: {e}")
        
        df = auto_label_clips()
        print(f"\n🎯 Auto-labeling pipeline completed!")
        print(f"📁 Updated file: {csv_path}")
    except Exception as e:
        print(f"❌ Error during auto-labeling: {e}")
        raise

if __name__ == "__main__":
    main() 