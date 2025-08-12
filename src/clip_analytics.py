#!/usr/bin/env python3
"""
Clip Analytics Module

This module provides functions to log and update engagement data for clips
in the clip_analytics table. It includes functions for:
- Logging initial analytics data
- Updating engagement metrics
- Fetching analytics data
- Batch operations for nightly feedback loops
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase library not available")

class ClipAnalytics:
    """Class to handle clip analytics operations"""
    
    def __init__(self):
        """Initialize the ClipAnalytics class"""
        self.supabase = None
        if SUPABASE_AVAILABLE:
            self._init_supabase()
    
    def _init_supabase(self):
        """Initialize Supabase client"""
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")
            
            if supabase_url and supabase_key:
                self.supabase = create_client(supabase_url, supabase_key)
                logger.info("✅ Supabase client initialized for clip analytics")
            else:
                logger.warning("⚠️  Supabase credentials not found")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase: {e}")
    
    def log_initial_analytics(self, clip_id: str, auto_label: Optional[str] = None) -> bool:
        """
        Log initial analytics data for a clip (post-upload)
        
        Args:
            clip_id: The unique identifier for the clip
            auto_label: The predicted label from the model
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.supabase:
            logger.error("❌ Supabase not available")
            return False
        
        try:
            # Create initial analytics record with zero values
            data = {
                "clip_id": clip_id,
                "views": 0,
                "likes": 0,
                "comments": 0,
                "watch_time": 0,
                "engagement_score": 0.0,
                "auto_label": auto_label
            }
            
            response = self.supabase.table("clip_analytics").insert(data).execute()
            
            if response.data:
                logger.info(f"✅ Initial analytics logged for clip: {clip_id}")
                return True
            else:
                logger.error(f"❌ Failed to log initial analytics for clip: {clip_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error logging initial analytics for {clip_id}: {e}")
            return False
    
    def update_engagement_metrics(self, clip_id: str, **metrics) -> bool:
        """
        Update engagement metrics for a clip
        
        Args:
            clip_id: The unique identifier for the clip
            **metrics: Keyword arguments for metrics (views, likes, comments, watch_time)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.supabase:
            logger.error("❌ Supabase not available")
            return False
        
        try:
            # Call the upsert function
            response = self.supabase.rpc(
                "upsert_clip_analytics",
                {
                    "p_clip_id": clip_id,
                    "p_views": metrics.get("views"),
                    "p_likes": metrics.get("likes"),
                    "p_comments": metrics.get("comments"),
                    "p_watch_time": metrics.get("watch_time"),
                    "p_auto_label": metrics.get("auto_label")
                }
            ).execute()
            
            logger.info(f"✅ Engagement metrics updated for clip: {clip_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating engagement metrics for {clip_id}: {e}")
            return False
    
    def get_clip_analytics(self, clip_id: str) -> Optional[Dict]:
        """
        Get analytics data for a specific clip
        
        Args:
            clip_id: The unique identifier for the clip
            
        Returns:
            Dict: Analytics data or None if not found
        """
        if not self.supabase:
            logger.error("❌ Supabase not available")
            return None
        
        try:
            response = self.supabase.table("clip_analytics").select("*").eq("clip_id", clip_id).execute()
            
            if response.data:
                return response.data[0]
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ Error fetching analytics for {clip_id}: {e}")
            return None
    
    def get_top_performing_clips(self, limit: int = 10, days: int = 30) -> List[Dict]:
        """
        Get top performing clips based on engagement score
        
        Args:
            limit: Number of clips to return
            days: Number of days to look back
            
        Returns:
            List[Dict]: List of top performing clips with analytics
        """
        if not self.supabase:
            logger.error("❌ Supabase not available")
            return []
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            response = self.supabase.table("clip_analytics")\
                .select("*, clips!inner(*)")\
                .gte("updated_at", cutoff_date.isoformat())\
                .order("engagement_score", desc=True)\
                .limit(limit)\
                .execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"❌ Error fetching top performing clips: {e}")
            return []
    
    def get_clips_needing_feedback(self, min_views: int = 10, days: int = 7) -> List[Dict]:
        """
        Get clips that need feedback based on engagement metrics
        
        Args:
            min_views: Minimum views required to consider for feedback
            days: Number of days to look back
            
        Returns:
            List[Dict]: List of clips needing feedback
        """
        if not self.supabase:
            logger.error("❌ Supabase not available")
            return []
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            response = self.supabase.table("clip_analytics")\
                .select("*, clips!inner(*)")\
                .gte("updated_at", cutoff_date.isoformat())\
                .gte("views", min_views)\
                .is_("clips.label", "null")\
                .order("engagement_score", desc=True)\
                .execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"❌ Error fetching clips needing feedback: {e}")
            return []
    
    def batch_update_analytics(self, analytics_data: List[Dict]) -> bool:
        """
        Batch update analytics data for multiple clips
        
        Args:
            analytics_data: List of dictionaries with clip_id and metrics
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.supabase:
            logger.error("❌ Supabase not available")
            return False
        
        try:
            success_count = 0
            total_count = len(analytics_data)
            
            for data in analytics_data:
                clip_id = data.get("clip_id")
                if clip_id:
                    success = self.update_engagement_metrics(clip_id, **data)
                    if success:
                        success_count += 1
            
            logger.info(f"✅ Batch update completed: {success_count}/{total_count} successful")
            return success_count == total_count
            
        except Exception as e:
            logger.error(f"❌ Error in batch update: {e}")
            return False
    
    def simulate_engagement_data(self, clip_id: str) -> Dict:
        """
        Simulate engagement data for testing purposes
        
        Args:
            clip_id: The clip ID to simulate data for
            
        Returns:
            Dict: Simulated engagement metrics
        """
        import random
        
        # Simulate realistic engagement data
        views = random.randint(10, 1000)
        likes = random.randint(0, int(views * 0.1))  # 0-10% like rate
        comments = random.randint(0, int(views * 0.02))  # 0-2% comment rate
        watch_time = random.randint(30, 300)  # 30 seconds to 5 minutes
        
        return {
            "clip_id": clip_id,
            "views": views,
            "likes": likes,
            "comments": comments,
            "watch_time": watch_time
        }

# Global instance
clip_analytics = ClipAnalytics()

# Convenience functions
def log_clip_analytics(clip_id: str, auto_label: Optional[str] = None) -> bool:
    """Log initial analytics for a clip"""
    return clip_analytics.log_initial_analytics(clip_id, auto_label)

def update_clip_metrics(clip_id: str, **metrics) -> bool:
    """Update engagement metrics for a clip"""
    return clip_analytics.update_engagement_metrics(clip_id, **metrics)

def get_clip_analytics_data(clip_id: str) -> Optional[Dict]:
    """Get analytics data for a clip"""
    return clip_analytics.get_clip_analytics(clip_id)

def get_top_clips(limit: int = 10, days: int = 30) -> List[Dict]:
    """Get top performing clips"""
    return clip_analytics.get_top_performing_clips(limit, days)

def get_clips_for_feedback(min_views: int = 10, days: int = 7) -> List[Dict]:
    """Get clips that need feedback"""
    return clip_analytics.get_clips_needing_feedback(min_views, days)

def batch_update_analytics_data(analytics_data: List[Dict]) -> bool:
    """Batch update analytics data"""
    return clip_analytics.batch_update_analytics(analytics_data)

def log_clip_analytics_data(clip_id: str, engagement_data: dict, auto_label: str = None):
    """
    Log analytics data for a clip to the clip_analytics table.
    
    Args:
        clip_id: The unique identifier for the clip
        engagement_data: Dictionary containing engagement metrics
        auto_label: The predicted label from the model
    """
    if not clip_analytics.supabase:
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