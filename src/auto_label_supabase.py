#!/usr/bin/env python3
"""
Auto-label clips in Supabase based on engagement metrics.
This module provides auto-labeling functionality for clips stored in Supabase.
"""

import os
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_engagement_score(views: int, watch_time: float, likes: int, comments: int) -> float:
    """
    Calculate engagement score based on metrics.
    
    Args:
        views: Number of views
        watch_time: Watch time in seconds
        likes: Number of likes
        comments: Number of comments
        
    Returns:
        float: Engagement score (0-1)
    """
    # Normalize metrics (you can adjust these weights)
    view_score = min(views / 1000, 1.0)  # Cap at 1000 views
    watch_score = min(watch_time / 300, 1.0)  # Cap at 5 minutes
    like_score = min(likes / 100, 1.0)  # Cap at 100 likes
    comment_score = min(comments / 50, 1.0)  # Cap at 50 comments
    
    # Weighted average
    engagement_score = (
        view_score * 0.3 +
        watch_score * 0.3 +
        like_score * 0.2 +
        comment_score * 0.2
    )
    
    return round(engagement_score, 3)

def assign_auto_label(views: int, engagement_score: float) -> float:
    """
    Assign auto label based on views and engagement score.
    
    Args:
        views: Number of views
        engagement_score: Calculated engagement score
        
    Returns:
        float: Auto label (0, 0.5, or 1)
    """
    # High engagement threshold
    if engagement_score >= 0.7 and views >= 500:
        return 1.0
    # Medium engagement - needs review
    elif engagement_score >= 0.4 or views >= 200:
        return 0.5
    # Low engagement
    else:
        return 0.0

def assign_label_type(auto_label: float) -> str:
    """
    Assign label_type based on auto_label value.
    
    Args:
        auto_label: Auto label value
        
    Returns:
        str: Label type ('auto' or 'review_needed')
    """
    if auto_label == 0.5:
        return 'review_needed'
    else:
        return 'auto'

def auto_label_supabase_clips():
    """
    Auto-label clips in Supabase based on engagement metrics.
    """
    try:
        from src.supabase_integration import supabase_manager
        
        if not supabase_manager.initialized:
            logger.error("❌ Supabase not initialized")
            return False
        
        print("📊 Loading clips from Supabase...")
        
        # Get all clips that need auto-labeling (no auto_label or empty)
        result = supabase_manager.client.table("clips") \
            .select("*") \
            .or_("auto_label.is.null,auto_label.eq.") \
            .execute()
        
        clips = result.data if result.data else []
        
        if not clips:
            print("🎉 No clips need auto-labeling!")
            return True
        
        print(f"✅ Found {len(clips)} clips to auto-label")
        
        updated_count = 0
        
        for clip in clips:
            # Get engagement metrics
            views = clip.get('views', 0)
            watch_time = clip.get('watch_time', 0.0)
            likes = clip.get('likes', 0)
            comments = clip.get('comments', 0)
            
            # Calculate engagement score
            engagement_score = calculate_engagement_score(views, watch_time, likes, comments)
            
            # Assign auto label
            auto_label = assign_auto_label(views, engagement_score)
            
            # Assign label type
            label_type = assign_label_type(auto_label)
            
            # Update the clip in Supabase
            update_result = supabase_manager.client.table("clips") \
                .update({
                    "auto_label": auto_label,
                    "label_type": label_type
                }) \
                .eq("clip_id", clip['clip_id']) \
                .execute()
            
            if update_result.data:
                updated_count += 1
                print(f"✅ Auto-labeled clip {clip['clip_id'][:8]}... as {auto_label}")
            else:
                print(f"❌ Failed to update clip {clip['clip_id'][:8]}...")
        
        # Print summary
        print(f"\n📈 Auto-labeling Summary:")
        print("-" * 40)
        print(f"Total clips processed: {len(clips)}")
        print(f"Successfully updated: {updated_count}")
        
        # Get updated counts by auto_label
        result = supabase_manager.client.table("clips") \
            .select("auto_label", count="exact") \
            .execute()
        
        if result.data:
            auto_label_counts = {}
            for item in result.data:
                label = item.get('auto_label')
                if label is not None:
                    auto_label_counts[label] = auto_label_counts.get(label, 0) + 1
            
            print(f"\n📊 Auto-label distribution:")
            for label, count in auto_label_counts.items():
                print(f"   {label}: {count} clips")
        
        print("✅ Auto-labeling completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during auto-labeling: {e}")
        return False

def update_clip_engagement(clip_id: str, views: int = None, watch_time: float = None, 
                          likes: int = None, comments: int = None) -> bool:
    """
    Update engagement metrics for a specific clip.
    
    Args:
        clip_id: The clip ID to update
        views: Number of views
        watch_time: Watch time in seconds
        likes: Number of likes
        comments: Number of comments
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from src.supabase_integration import supabase_manager
        
        if not supabase_manager.initialized:
            logger.error("❌ Supabase not initialized")
            return False
        
        # Prepare update data
        update_data = {}
        if views is not None:
            update_data['views'] = views
        if watch_time is not None:
            update_data['watch_time'] = watch_time
        if likes is not None:
            update_data['likes'] = likes
        if comments is not None:
            update_data['comments'] = comments
        
        if not update_data:
            logger.warning("No engagement metrics provided for update")
            return False
        
        # Update the clip
        result = supabase_manager.client.table("clips") \
            .update(update_data) \
            .eq("clip_id", clip_id) \
            .execute()
        
        if result.data:
            logger.info(f"✅ Updated engagement metrics for clip {clip_id[:8]}...")
            return True
        else:
            logger.error(f"❌ Failed to update engagement metrics for clip {clip_id[:8]}...")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error updating engagement metrics: {e}")
        return False

def main():
    """Main function to run the auto-labeling pipeline."""
    try:
        success = auto_label_supabase_clips()
        if success:
            print(f"\n🎯 Auto-labeling pipeline completed!")
        else:
            print(f"\n❌ Auto-labeling pipeline failed!")
    except Exception as e:
        print(f"❌ Error during auto-labeling: {e}")
        raise

if __name__ == "__main__":
    main() 